import type { AssetSource } from './story'

export interface Character {
  id: string
  name: string
  generationSource: 'ai' | 'manual'
  role: string
  appearance: string
  hairstyle: string
  clothing: string
  signatureTraits: string
  personality: string
  imagePrompt: string
  referenceImageUrl: string
  referenceImageSource: AssetSource | null
  confirmed: boolean
}

export type CharacterEditableField = Exclude<
  keyof Character,
  'id' | 'generationSource' | 'imagePrompt' | 'referenceImageUrl' | 'referenceImageSource' | 'confirmed'
>
