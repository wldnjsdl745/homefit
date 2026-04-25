export class IdFactory {
  private counter = 0;

  next(prefix: string): string {
    this.counter += 1;
    return `${prefix}_${Date.now()}_${this.counter}`;
  }
}
