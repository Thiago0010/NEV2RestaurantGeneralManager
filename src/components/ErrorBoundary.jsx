import React from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
          <div className="w-full max-w-md">
            <div className="bg-card rounded-2xl shadow-sm border border-border p-8">
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-destructive/10 mb-4">
                  <AlertCircle className="w-7 h-7 text-destructive" aria-hidden="true" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-foreground">Algo deu errado</h1>
                <p className="text-muted-foreground mt-2">Ocorreu um erro inesperado ao carregar a página.</p>
              </div>
              
              <details className="mb-6 p-4 bg-muted rounded-lg text-left">
                <summary className="font-medium text-foreground cursor-pointer">
                  Detalhes do erro (para desenvolvedores)
                </summary>
                <pre className="mt-4 p-4 bg-background rounded text-xs text-muted-foreground overflow-auto max-h-64">
                  {this.state.error && this.state.error.toString()}
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>

              <div className="flex gap-2">
                <Button 
                  variant="outline"
                  onClick={() => window.location.reload()}
                  className="flex-1"
                >
                  Recarregar página
                </Button>
                <Button 
                  onClick={() => window.location.href = "/login"}
                  className="flex-1"
                >
                  Ir para Login
                </Button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;