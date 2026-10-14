'use client'

import Image from '@/components/ui/image'
import { ImageOff } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { ASPECT_RATIO_VALUES } from '@/types/storyboard'
import { useStudio } from './studio-provider'

export function ComicPreviewDialog() {
  const { project, previewOpen, setPreviewOpen } = useStudio()
  const missing = project.panels.filter((p) => !p.imageUrl).length

  return (
    <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
      <DialogContent className="max-h-[90vh] gap-3 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{project.title || '未命名项目'}</DialogTitle>
          <DialogDescription>
            条漫预览 · {project.panels.length} 格{missing > 0 && ` · ${missing} 格尚未生成画面`}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[70vh] rounded-md">
          <div className="flex flex-col gap-3 bg-neutral-100 p-4">
            {project.panels.map((panel, index) => (
              <figure
                key={panel.id}
                className="relative overflow-hidden border-[3px] border-neutral-900 bg-neutral-200"
                style={{ aspectRatio: ASPECT_RATIO_VALUES[panel.aspectRatio] }}
              >
                {panel.imageUrl ? (
                  <Image src={panel.imageUrl} alt={`第 ${panel.panelNumber} 格：${panel.scene}`} fill sizes="640px" className="object-cover" />
                ) : (
                  <div className="flex h-full items-center justify-center text-neutral-500">
                    <ImageOff className="size-6" aria-label="尚未生成画面" />
                  </div>
                )}
                {panel.dialogue.trim() && (
                  <figcaption
                    className={cn(
                      'absolute top-[5%] max-w-[60%] rounded-[1.25rem] border-2 border-neutral-900 bg-white px-3 py-1.5 text-center text-sm font-bold text-neutral-900',
                      index % 2 ? 'right-[4%]' : 'left-[4%]',
                    )}
                  >
                    {panel.dialogue}
                  </figcaption>
                )}
              </figure>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
