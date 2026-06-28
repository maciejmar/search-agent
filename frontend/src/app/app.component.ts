import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';

interface UploadedDocument {
  fileName: string;
  fileType: string;
  charCount: number;
}

interface FieldVariant {
  value: string;
  normalizedValue: string;
  documents: string[];
  occurrences: number;
}

interface PartyFieldResult {
  field: string;
  consistent: boolean;
  variants: FieldVariant[];
}

interface PartyIssue {
  field: string;
  severity: 'warning' | 'error';
  message: string;
  variants: string[];
  documents: string[];
}

interface PartyResult {
  displayName: string;
  normalizedName: string;
  partyType: 'person' | 'organization' | 'unknown';
  documents: string[];
  fields: PartyFieldResult[];
  issues: PartyIssue[];
}

interface GlobalIssue {
  severity: 'info' | 'warning' | 'error';
  message: string;
  documents: string[];
}

interface UsageSummary {
  provider: 'openai' | 'local';
  mode: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  cachedInputTokens: number;
  estimatedCostUsd: number;
  pricingInputUsdPer1M: number;
  pricingOutputUsdPer1M: number;
  pricingCachedInputUsdPer1M: number;
}

interface UsageRun {
  timestamp: string;
  provider: 'openai' | 'local';
  mode: string;
  model: string;
  documentNames: string[];
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  cachedInputTokens: number;
  estimatedCostUsd: number;
  status: 'success' | 'fallback' | 'error';
}

interface UsageTotals {
  requestCount: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalTokens: number;
  totalCachedInputTokens: number;
  totalCostUsd: number;
}

interface UsageDashboard {
  totals: UsageTotals;
  recentRuns: UsageRun[];
}

interface OpenAIDebugResponse {
  configured: boolean;
  model: string;
  status: 'ok' | 'error';
  provider: 'openai';
  message: string;
  errorType: string | null;
}

interface AnalysisResponse {
  documents: UploadedDocument[];
  parties: PartyResult[];
  globalIssues: GlobalIssue[];
  summary: string;
  usage: UsageSummary | null;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  private readonly http = inject(HttpClient);

  activeTab: 'analysis' | 'usage' = 'analysis';
  selectedFiles: File[] = [];
  isSubmitting = false;
  isLoadingUsage = false;
  isLoadingOpenAIDebug = false;
  errorMessage = '';
  usageErrorMessage = '';
  openAIDebugErrorMessage = '';
  analysisResult: AnalysisResponse | null = null;
  usageDashboard: UsageDashboard | null = null;
  openAIDebug: OpenAIDebugResponse | null = null;

  constructor() {
    this.loadUsageDashboard();
  }

  setActiveTab(tab: 'analysis' | 'usage'): void {
    this.activeTab = tab;
    if (tab === 'usage') {
      if (!this.usageDashboard) {
        this.loadUsageDashboard();
      }
      if (!this.openAIDebug) {
        this.loadOpenAIDebug();
      }
    }
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files ? Array.from(input.files) : [];
    this.selectedFiles = files;
    this.errorMessage = '';
    this.analysisResult = null;
  }

  removeFile(index: number): void {
    this.selectedFiles = this.selectedFiles.filter((_, fileIndex) => fileIndex !== index);
  }

  analyzeDocuments(): void {
    if (!this.selectedFiles.length) {
      this.errorMessage = 'Wybierz co najmniej jeden dokument do analizy.';
      return;
    }

    const formData = new FormData();
    this.selectedFiles.forEach((file) => formData.append('files', file, file.name));

    this.isSubmitting = true;
    this.errorMessage = '';
    this.analysisResult = null;

    this.http.post<AnalysisResponse>('/api/analyze', formData).subscribe({
      next: (response) => {
        this.analysisResult = response;
        this.isSubmitting = false;
        this.loadUsageDashboard();
        this.loadOpenAIDebug();
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage = typeof error.error?.detail === 'string'
          ? error.error.detail
          : 'Nie uda\u0142o si\u0119 przeanalizowa\u0107 dokument\u00f3w.';
        this.isSubmitting = false;
      }
    });
  }

  loadUsageDashboard(): void {
    this.isLoadingUsage = true;
    this.usageErrorMessage = '';
    this.http.get<UsageDashboard>('/api/usage').subscribe({
      next: (dashboard) => {
        this.usageDashboard = dashboard;
        this.isLoadingUsage = false;
      },
      error: () => {
        this.usageErrorMessage = 'Nie uda\u0142o si\u0119 pobra\u0107 statystyk zu\u017cycia API.';
        this.isLoadingUsage = false;
      }
    });
  }

  loadOpenAIDebug(): void {
    this.isLoadingOpenAIDebug = true;
    this.openAIDebugErrorMessage = '';
    this.http.get<OpenAIDebugResponse>('/api/debug/openai').subscribe({
      next: (response) => {
        this.openAIDebug = response;
        this.isLoadingOpenAIDebug = false;
      },
      error: () => {
        this.openAIDebugErrorMessage = 'Nie uda\u0142o si\u0119 pobra\u0107 diagnostyki OpenAI.';
        this.isLoadingOpenAIDebug = false;
      }
    });
  }

  trackParty(_: number, party: PartyResult): string {
    return party.normalizedName;
  }

  formatUsd(value: number): string {
    return new Intl.NumberFormat('pl-PL', {
      minimumFractionDigits: 4,
      maximumFractionDigits: 6
    }).format(value);
  }

  formatTimestamp(value: string): string {
    return new Date(value).toLocaleString('pl-PL');
  }
}