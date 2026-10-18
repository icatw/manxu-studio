import { describe, expect, it } from "vitest"
import { mentionedCastNotBound } from "./cast-mention"

describe("mentionedCastNotBound", () => {
  const cast = [
    { id: "gu", name: "顾承川" },
    { id: "lin", name: "林澈" },
    { id: "zero", name: "零" },
  ]

  it("flags cast names in dialogue that are not bound", () => {
    const missing = mentionedCastNotBound(cast, ["gu"], "林澈：今晚别出门。零，跟上。")
    expect(missing.map((item) => item.id)).toEqual(["lin", "zero"])
  })

  it("returns empty when bound or no mention", () => {
    expect(mentionedCastNotBound(cast, ["lin"], "林澈点头。")).toEqual([])
    expect(mentionedCastNotBound(cast, [], "空镜：港口夜色")).toEqual([])
  })
})
