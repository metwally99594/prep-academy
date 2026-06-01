import { Component } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  handleRecovery = () => {
    this.setState({ error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.error) {
      return (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center space-y-3 max-w-xs">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
            <p className="text-sm text-white/60">
              Ein Fehler ist in der Konversation aufgetreten.
            </p>
            <p className="text-xs text-white/40">
              Die Konversation wird zurückgesetzt — der Verlauf bleibt in der Seitenleiste erhalten.
            </p>
            <Button variant="outline" size="sm" onClick={this.handleRecovery}
              className="gap-2 border-white/10 text-white/70 hover:text-white">
              <RefreshCw className="w-3.5 h-3.5" />
              Konversation zurücksetzen
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
