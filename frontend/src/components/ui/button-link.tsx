import Link from '@/components/ui/link'
import type { ComponentProps } from 'react'
import type { VariantProps } from 'class-variance-authority'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type ButtonLinkProps = ComponentProps<typeof Link> & VariantProps<typeof buttonVariants>

export function ButtonLink({ className, variant, size, ...props }: ButtonLinkProps) {
  return <Link data-slot="button" className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
