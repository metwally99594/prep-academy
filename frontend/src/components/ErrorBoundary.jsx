import React from 'react';
import { Button } from "@/components/ui/button";
import { RefreshCcw, AlertTriangle } from "lucide-react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('App Error:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
          <div className="glass-card rounded-2xl p-8 max-w-md text-center">
            <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-amber-500" />
            </div>
            <h2 className="text-2xl font-bold mb-4">Etwas ist schief gelaufen</h2>
            <p className="text-muted-foreground mb-6">
              Ein Fehler ist aufgetreten. Bitte laden Sie die Seite neu.
              <br />
              <span className="text-sm">
                Hinweis: Bitte deaktivieren Sie die automatische Seitenübersetzung, da sie Probleme verursachen kann.
              </span>
            </p>
            {this.state.error && (
              <details className="mb-4 text-left bg-red-50 dark:bg-red-950/30 rounded-lg p-3 overflow-auto max-h-40">
                <summary className="text-sm font-medium text-red-600 dark:text-red-400 cursor-pointer">
                  Fehlerdetails
                </summary>
                <pre className="mt-2 text-xs text-red-700 dark:text-red-300 whitespace-pre-wrap break-all">
                  {this.state.error.message}
                  {'\n\n'}
                  {this.state.error.stack?.split('\n').slice(1, 6).join('\n')}
                </pre>
              </details>
            )}
            <Button onClick={this.handleReload} className="gap-2">
              <RefreshCcw className="w-4 h-4" />
              Seite neu laden
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
