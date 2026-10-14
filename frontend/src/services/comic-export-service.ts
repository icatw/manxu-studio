import { ASSET_SOURCE_SHORT } from '@/lib/asset-labels'
import { ASPECT_RATIO_VALUES, type ComicProject, type StoryboardPanel } from '@/types/storyboard'

export interface ComicExportOptions {
  pageWidth?: number
  includeDialogue?: boolean
}

export interface ComicExportService {
  composePage(project: ComicProject, options?: ComicExportOptions): Promise<HTMLCanvasElement>
  exportPng(project: ComicProject, options?: ComicExportOptions): Promise<void>
}

const FONT_STACK = '"PingFang SC", "Noto Sans SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif'
const PAGE_BG = '#f4f1ea'
const INK = '#111111'

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`图片加载失败：${src}`))
    img.src = src
  })
}

function drawCover(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  x: number,
  y: number,
  w: number,
  h: number,
) {
  const scale = Math.max(w / img.naturalWidth, h / img.naturalHeight)
  const sw = w / scale
  const sh = h / scale
  const sx = (img.naturalWidth - sw) / 2
  const sy = (img.naturalHeight - sh) / 2
  ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h)
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number) {
  const lines: string[] = []
  for (const paragraph of text.split('\n')) {
    let line = ''
    for (const char of Array.from(paragraph)) {
      const next = line + char
      if (ctx.measureText(next).width > maxWidth && line) {
        lines.push(line)
        line = char
      } else {
        line = next
      }
    }
    lines.push(line)
  }
  return lines
}

function drawBubble(
  ctx: CanvasRenderingContext2D,
  text: string,
  panelX: number,
  panelY: number,
  panelW: number,
  panelH: number,
  alignRight: boolean,
) {
  const fontSize = Math.round(Math.max(22, Math.min(34, panelW / 24)))
  ctx.font = `700 ${fontSize}px ${FONT_STACK}`
  const padX = fontSize * 0.8
  const padY = fontSize * 0.6
  const lineHeight = fontSize * 1.35
  const maxTextW = panelW * 0.58 - padX * 2
  const lines = wrapText(ctx, text, maxTextW).slice(0, 4)
  const textW = Math.max(...lines.map((l) => ctx.measureText(l).width))
  const bw = textW + padX * 2
  const bh = lines.length * lineHeight + padY * 2 - (lineHeight - fontSize)
  const inset = panelW * 0.04
  const bx = alignRight ? panelX + panelW - bw - inset : panelX + inset
  const by = panelY + Math.min(inset, panelH * 0.06)
  const radius = Math.min(bh / 2, fontSize * 1.1)

  ctx.save()
  ctx.shadowColor = 'rgba(0,0,0,0.25)'
  ctx.shadowBlur = 8
  ctx.fillStyle = '#ffffff'
  ctx.strokeStyle = INK
  ctx.lineWidth = 3

  ctx.beginPath()
  ctx.roundRect(bx, by, bw, bh, radius)
  ctx.fill()
  ctx.shadowBlur = 0
  ctx.stroke()

  const tailBaseX = alignRight ? bx + bw * 0.7 : bx + bw * 0.3
  const tailDir = alignRight ? 1 : -1
  ctx.beginPath()
  ctx.moveTo(tailBaseX - 12, by + bh - 2)
  ctx.lineTo(tailBaseX + tailDir * 18, by + bh + fontSize * 0.9)
  ctx.lineTo(tailBaseX + 12, by + bh - 2)
  ctx.closePath()
  ctx.fill()
  ctx.beginPath()
  ctx.moveTo(tailBaseX - 12, by + bh)
  ctx.lineTo(tailBaseX + tailDir * 18, by + bh + fontSize * 0.9)
  ctx.lineTo(tailBaseX + 12, by + bh)
  ctx.stroke()
  ctx.restore()

  ctx.fillStyle = INK
  ctx.font = `700 ${fontSize}px ${FONT_STACK}`
  ctx.textBaseline = 'top'
  ctx.textAlign = 'center'
  lines.forEach((line, i) => {
    ctx.fillText(line, bx + bw / 2, by + padY + i * lineHeight)
  })
  ctx.textAlign = 'left'
}

function drawPanelNumber(ctx: CanvasRenderingContext2D, n: number, x: number, y: number, h: number) {
  const size = 34
  ctx.fillStyle = INK
  ctx.fillRect(x, y + h - size, size + 8, size)
  ctx.fillStyle = '#ffffff'
  ctx.font = `700 20px ${FONT_STACK}`
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'center'
  ctx.fillText(String(n), x + (size + 8) / 2, y + h - size / 2)
  ctx.textAlign = 'left'
}

async function composePage(
  project: ComicProject,
  { pageWidth = 1800, includeDialogue = true }: ComicExportOptions = {},
) {
  const panels = project.panels
  if (panels.length === 0) throw new Error('没有可导出的分镜')

  const margin = Math.round(pageWidth * 0.035)
  const gutter = Math.round(pageWidth * 0.016)
  const headerH = Math.round(pageWidth * 0.07)
  const footerH = Math.round(pageWidth * 0.03)
  const cols = panels.length === 1 ? 1 : 2
  const cellW = (pageWidth - margin * 2 - gutter * (cols - 1)) / cols

  const rows: StoryboardPanel[][] = []
  for (let i = 0; i < panels.length; i += cols) rows.push(panels.slice(i, i + cols))
  const rowHeights = rows.map((row) =>
    Math.max(...row.map((p) => cellW / ASPECT_RATIO_VALUES[p.aspectRatio])),
  )
  const pageHeight =
    headerH + rowHeights.reduce((a, b) => a + b, 0) + gutter * (rows.length - 1) + footerH + margin * 2

  const images = await Promise.all(
    panels.map((p) => (p.imageUrl ? loadImage(p.imageUrl).catch(() => null) : Promise.resolve(null))),
  )

  const canvas = document.createElement('canvas')
  canvas.width = pageWidth
  canvas.height = Math.round(pageHeight)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('浏览器不支持 Canvas 2D')

  ctx.fillStyle = PAGE_BG
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.fillStyle = INK
  ctx.textBaseline = 'alphabetic'
  ctx.font = `800 ${Math.round(headerH * 0.48)}px ${FONT_STACK}`
  ctx.fillText(project.title || '未命名项目', margin, margin + headerH * 0.55)
  ctx.font = `500 ${Math.round(headerH * 0.2)}px ${FONT_STACK}`
  ctx.fillStyle = '#555555'
  ctx.fillText(
    `${project.story.genre} · ${project.story.style} · 共 ${panels.length} 格`,
    margin,
    margin + headerH * 0.88,
  )

  let y = margin + headerH
  let panelIndex = 0
  rows.forEach((row, r) => {
    row.forEach((panel, c) => {
      const x = margin + c * (cellW + gutter)
      const h = cellW / ASPECT_RATIO_VALUES[panel.aspectRatio]
      const img = images[panelIndex]

      if (img) {
        drawCover(ctx, img, x, y, cellW, h)
      } else {
        ctx.fillStyle = '#d9d4ca'
        ctx.fillRect(x, y, cellW, h)
        ctx.fillStyle = '#7a756c'
        ctx.font = `600 28px ${FONT_STACK}`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(`第 ${panel.panelNumber} 格 · 尚未生成画面`, x + cellW / 2, y + h / 2)
        ctx.textAlign = 'left'
      }

      ctx.strokeStyle = INK
      ctx.lineWidth = 6
      ctx.strokeRect(x, y, cellW, h)

      if (includeDialogue && panel.dialogue.trim()) {
        drawBubble(ctx, panel.dialogue.trim(), x, y, cellW, h, panelIndex % 2 === 1)
      }
      drawPanelNumber(ctx, panel.panelNumber, x, y, h)
      panelIndex++
    })
    y += rowHeights[r] + gutter
  })

  const sources = new Set(panels.map((p) => p.imageSource).filter(Boolean))
  const sourceNote = [...sources].map((s) => ASSET_SOURCE_SHORT[s!]).join(' / ')
  ctx.fillStyle = '#7a756c'
  ctx.font = `500 ${Math.round(footerH * 0.5)}px ${FONT_STACK}`
  ctx.textBaseline = 'alphabetic'
  ctx.fillText(
    `漫序 Studio 导出${sourceNote ? ` · 画面来源：${sourceNote}` : ''}`,
    margin,
    canvas.height - margin * 0.6,
  )

  return canvas
}

function sanitizeFilename(name: string) {
  return (name || 'manxu-comic').replace(/[\\/:*?"<>|]/g, '_').slice(0, 60)
}

export const comicExportService: ComicExportService = {
  composePage,
  async exportPng(project, options) {
    const canvas = await composePage(project, options)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('PNG 编码失败')
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${sanitizeFilename(project.title)}.png`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}
