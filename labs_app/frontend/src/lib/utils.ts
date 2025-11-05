import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function escapeHtml(value: string): string {
  if (!value) {
    return ''
  }
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function plainTextToHtml(text: string): string {
  if (!text) {
    return ''
  }

  const normalized = text.replace(/\r\n?/g, '\n').trim()
  if (!normalized) {
    return ''
  }

  const splitIntoParagraphs = (value: string) => {
    const explicitParagraphs = value
      .split(/\n{2,}/)
      .map((item) => item.trim())
      .filter(Boolean)

    if (explicitParagraphs.length > 1) {
      return explicitParagraphs
    }

    const sentences = value
      .split(/(?<=[.!?])\s+(?=[A-ZÆØÅÄÖÜÉÈ0-9«(])/)
      .map((sentence) => sentence.trim())
      .filter(Boolean)

    if (sentences.length <= 1) {
      return [value.trim()]
    }

    const paragraphs: string[] = []
    let buffer: string[] = []
    let bufferLength = 0

    sentences.forEach((sentence) => {
      buffer.push(sentence)
      bufferLength += sentence.length

      const shouldFlush =
        bufferLength >= 220 || sentence.endsWith(':') || buffer.length >= 2

      if (shouldFlush) {
        paragraphs.push(buffer.join(' ').trim())
        buffer = []
        bufferLength = 0
      }
    })

    if (buffer.length) {
      paragraphs.push(buffer.join(' ').trim())
    }

    return paragraphs
  }

  const renderListFromParagraph = (paragraph: string) => {
    const bulletLinePattern =
      /^[\u2022\u2023\u2043\u2219\u25A0\u25AA\u25CB\u25CF\u25E6\u30FB•‣◦⁃\-–—*+]\s+/
    const orderedLinePattern = /^(?:\d+|[A-Za-z])([.)]|(?:\s+-))\s+/

    const stripHeadingFromItems = (items: string[]) =>
      items.map((line) => line.replace(/^\W+/, '').trim()).filter(Boolean)

    const buildListHtml = (
      heading: string | null,
      items: string[],
      type: 'ul' | 'ol'
    ) => {
      if (!items.length) {
        return ''
      }

      const headingHtml = heading
        ? `<p><strong>${escapeHtml(heading)}</strong></p>`
        : ''
      const itemsHtml = items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')

      return `${headingHtml}<${type}>${itemsHtml}</${type}>`
    }

    const colonIndex = paragraph.indexOf(':')
    if (colonIndex === -1) {
      const lines = paragraph
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)

      if (lines.length < 2) {
        return ''
      }

      const headingLine =
        lines.length > 2 && lines[0].endsWith(':')
          ? lines[0].slice(0, -1).trim()
          : null
      const listLines = headingLine ? lines.slice(1) : lines

      const isBulletList = listLines.every((line) => bulletLinePattern.test(line))
      if (isBulletList) {
        const items = listLines.map((line) => line.replace(bulletLinePattern, '').trim())
        return buildListHtml(headingLine, stripHeadingFromItems(items), 'ul')
      }

      const isOrderedList = listLines.every((line) => orderedLinePattern.test(line))
      if (isOrderedList) {
        const items = listLines.map((line) =>
          line.replace(orderedLinePattern, '').trim()
        )
        return buildListHtml(headingLine, stripHeadingFromItems(items), 'ol')
      }

      return ''
    }

    const lead = paragraph.slice(0, colonIndex).trim()
    const remainder = paragraph.slice(colonIndex + 1).trim()
    const listItems = remainder
      .split(/;\s+/)
      .map((item) => item.trim())
      .filter(Boolean)

    if (listItems.length < 2) {
      const heading =
        lead.endsWith(':') && lead.length > 1 ? lead.slice(0, -1).trim() : lead
      const remainderLines = remainder
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)

      if (remainderLines.length >= 1) {
        const isBullet = remainderLines.every((line) => bulletLinePattern.test(line))
        if (isBullet) {
          const items = remainderLines.map((line) =>
            line.replace(bulletLinePattern, '').trim()
          )
          return buildListHtml(heading, stripHeadingFromItems(items), 'ul')
        }

        const isOrdered = remainderLines.every((line) =>
          orderedLinePattern.test(line)
        )
        if (isOrdered) {
          const items = remainderLines.map((line) =>
            line.replace(orderedLinePattern, '').trim()
          )
          return buildListHtml(heading, stripHeadingFromItems(items), 'ol')
        }
      }

      return ''
    }

    const heading = escapeHtml(lead.endsWith(':') ? lead.slice(0, -1) : lead)
    const itemsHtml = listItems
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join('')

    return `<p><strong>${heading}:</strong></p><ul>${itemsHtml}</ul>`
  }

  return splitIntoParagraphs(normalized)
    .map((paragraph) => {
      const listHtml = renderListFromParagraph(paragraph)
      if (listHtml) {
        return listHtml
      }

      const escaped = escapeHtml(paragraph)
      return `<p>${escaped.replace(/\n+/g, '<br />')}</p>`
    })
    .join('')
}

const CONTROL_SEQUENCE_REGEX =
  /^\[(?:SOURCE|SESSION_ID|STATUS|CONTEXTS|CHUNK|DONE)\]/i
const JSON_LINE_REGEX = /^\s*[{[]/

export function sanitizeModelText(value?: string | null): string {
  if (!value) {
    return ''
  }

  const cleaned: string[] = []
  let previousBlank = false

  value.split(/\r?\n/).forEach((line) => {
    const trimmed = line.trim()

    if (!trimmed) {
      if (!previousBlank && cleaned.length) {
        cleaned.push('')
      }
      previousBlank = true
      return
    }

    if (CONTROL_SEQUENCE_REGEX.test(trimmed)) {
      return
    }

    if (JSON_LINE_REGEX.test(trimmed)) {
      // Skip standalone JSON fragments that occasionally leak into the stream.
      return
    }

    previousBlank = false
    cleaned.push(trimmed)
  })

  return cleaned.join('\n').trim()
}
