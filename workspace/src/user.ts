export type User = { id: string; name: string };

export function formatUser(user: User): string {
  // TODO: 处理空名字
  return user.name.trim();
}
