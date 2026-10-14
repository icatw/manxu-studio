import type { AssetSource } from './story'

export interface Character {
  id: string
  name: string
  role: string
  appearance: string
  hairstyle: string
  clothing: string
  signatureTraits: string
  personality: string
  referenceImageUrl: string
  referenceImageSource: AssetSource
  confirmed: boolean
}

export type CharacterEditableField = Exclude<
  keyof Character,
  'id' | 'referenceImageUrl' | 'referenceImageSource' | 'confirmed'
>
