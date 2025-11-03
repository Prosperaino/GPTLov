from __future__ import annotations

import logging
import shutil
import tarfile
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from zipfile import ZipFile

import httpx

from .ingest import build_chunks, extract_archives, iter_chunks
from .index import build_vector_store
from .search_backends import ElasticsearchBackend
from .settings import settings

logger = logging.getLogger(__name__)

LOVDATA_BASE_URL = "https://api.lovdata.no/v1/publicData/get/"
VECTOR_STORE_FILENAME = "vector_store.pkl"
DEFAULT_ARCHIVES = (
    "gjeldende-lover.tar.bz2",
    "gjeldende-sentrale-forskrifter.tar.bz2",
)


def download_archive(filename: str, dest_dir: Path, timeout: float = 30.0) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = dest_dir / filename
    if destination.exists():
        logger.info("Archive %s already present", filename)
        return destination

    url = f"{LOVDATA_BASE_URL}{filename}"
    logger.info("Downloading %s", url)
    with httpx.stream("GET", url, timeout=timeout) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)

    logger.info("Saved archive to %s", destination)
    return destination


def ensure_archives(filenames: Iterable[str] | None = None, force: bool = False) -> list[Path]:
    if filenames is None:
        filenames = settings.archives or DEFAULT_ARCHIVES
    raw_dir = settings.raw_data_dir
    paths: list[Path] = []
    for name in filenames:
        destination = raw_dir / name
        if force and destination.exists():
            destination.unlink()
        paths.append(download_archive(name, raw_dir))
    return paths


def _download_prebuilt_vector_store(url: str, workspace_dir: Path, force: bool = False) -> Path:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    store_path = workspace_dir / VECTOR_STORE_FILENAME
    if store_path.exists() and not force:
        logger.info("Vector store already present at %s", store_path)
        return store_path

    parsed = urlparse(url)
    suffixes = Path(parsed.path).suffixes
    archive_ext = "".join(suffixes)

    tmp_dir = workspace_dir / ".vector_store_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    download_target = tmp_dir / f"download{archive_ext or '.bin'}"
    logger.info("Downloading vector store from %s", url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        with download_target.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)

    def _finalize(src: Path) -> Path:
        if store_path.exists():
            store_path.unlink()
        shutil.move(str(src), str(store_path))
        return store_path

    archive_ext_lower = archive_ext.lower()
    if archive_ext_lower.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar")):
        logger.info("Extracting tar archive %s", download_target)
        with tarfile.open(download_target, "r:*") as tar:
            tar.extractall(tmp_dir)
        download_target.unlink()
    elif archive_ext_lower.endswith(".zip"):
        logger.info("Extracting zip archive %s", download_target)
        with ZipFile(download_target, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)
        download_target.unlink()
    elif archive_ext:
        logger.info("Storing downloaded vector store at %s", store_path)
        final_path = _finalize(download_target)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return final_path
    else:
        logger.info("Storing downloaded vector store at %s", store_path)
        final_path = _finalize(download_target)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return final_path

    candidates = list(tmp_dir.rglob(VECTOR_STORE_FILENAME))
    if not candidates:
        raise FileNotFoundError(
            f"Downloaded archive from {url} did not contain {VECTOR_STORE_FILENAME}"
        )
    vector_path = candidates[0]
    final_path = _finalize(vector_path)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    logger.info("Vector store extracted to %s", final_path)
    return final_path


def ensure_vector_store(force: bool = False) -> Path | None:
    if settings.search_backend == "elasticsearch":
        ensure_archives(force=force)
        workspace_dir = settings.workspace_dir
        extracted_root = workspace_dir / "extracted"
        extracted_dirs = extract_archives(settings.raw_data_dir, extracted_root, force=force)
        backend = ElasticsearchBackend(
            host=settings.es_host or "",
            index=settings.es_index,
            username=settings.es_username,
            password=settings.es_password,
            verify_certs=settings.es_verify_certs,
        )
        if not force and backend.has_documents():
            logger.info(
                "Elasticsearch index '%s' already populated; skipping re-indexing",
                settings.es_index,
            )
            return None
        chunk_iterator = iter_chunks(extracted_dirs)
        indexed = backend.index_documents(chunk_iterator, force=force)
        logger.info("Indexed %d document chunks into Elasticsearch index '%s'", indexed, settings.es_index)
        return None

    workspace_dir = settings.workspace_dir
    store_path = workspace_dir / VECTOR_STORE_FILENAME

    if settings.vector_store_url:
        logger.info("Using prebuilt vector store from %s", settings.vector_store_url)
        try:
            return _download_prebuilt_vector_store(
                settings.vector_store_url, workspace_dir, force=force
            )
        except Exception as exc:  # pragma: no cover - network failures
            logger.exception(
                "Failed to download vector store from %s", settings.vector_store_url
            )
            raise RuntimeError(
                "Unable to download prebuilt vector store; aborting startup"
            ) from exc

    if store_path.exists() and not force:
        logger.info("Vector store already exists at %s", store_path)
        return store_path

    ensure_archives(force=force)
    extracted_root = workspace_dir / "extracted"
    extracted_dirs = extract_archives(settings.raw_data_dir, extracted_root, force=force)
    chunks = build_chunks(extracted_dirs)
    logger.info("Built %d document chunks", len(chunks))
    path = build_vector_store(chunks, workspace_dir)
    logger.info("Vector store written to %s", path)
    return path
