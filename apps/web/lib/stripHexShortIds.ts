export const HEX_SHORTID_RE = / ?\[[0-9a-f]{6,8}\]/gi;

export function stripHexShortIds(text: string): string {
  return text.replace(HEX_SHORTID_RE, "");
}
