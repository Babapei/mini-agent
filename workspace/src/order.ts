export type Order = { id: string; amount: number };

export function total(orders: Order[]): number {
  // FIXME: 没有处理空数组
  return orders.reduce((sum, order) => sum + order.amount, 0);
}
