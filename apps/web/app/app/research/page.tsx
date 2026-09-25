import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";

export const metadata = {
  title: "AI Research",
  description: "RegimeX AI Quantitative Research Assistant",
};

export default function ResearchPage() {
  return (
    <div className="module-placeholder-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Research", isCurrent: true },
        ]}
      />

      <header className="page-header">
        <div className="page-header-title-row">
          <h1 className="page-title">AI Research Assistant</h1>
          <Badge variant="outline" size="md">
            Scheduled for V21
          </Badge>
        </div>
        <p className="page-subtitle">
          Grounded quantitative query assistant operating over platform models and regime data.
        </p>
      </header>

      <Card variant="elevated">
        <CardHeader>
          <CardTitle>Module Foundation Established</CardTitle>
          <CardDescription>
            Grounded LLM research agent design and knowledge base retrieval pipeline scheduled for Volume 21.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="placeholder-info-box">
            <p className="placeholder-info-text">
              Conversational quantitative research assistant, contextual code generation, and
              formula derivation tools will be integrated into this workspace.
            </p>
          </div>
          <div className="placeholder-actions">
            <Link href="/app">
              <Button variant="secondary">Back to Overview</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
