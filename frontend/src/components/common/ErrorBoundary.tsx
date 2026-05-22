import { Component, type ErrorInfo, type PropsWithChildren, type ReactNode } from "react";

type ErrorBoundaryState = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error(error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <main className="flex min-h-screen items-center justify-center bg-cream px-4 font-pixel">
          <div className="max-w-md border-[3px] border-ink bg-paper px-6 py-5 text-sm text-ink shadow-pixel">
            <div className="mb-2 text-base text-coral">! ERROR</div>
            화면을 불러오지 못했어요. 새로고침 후 다시 시도해주세요.
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}
