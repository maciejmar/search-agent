import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface UserSummary {
  id: number;
  email: string;
  fullName: string;
}

interface AuthResponse {
  accessToken: string;
  tokenType: 'bearer';
  user: UserSummary;
}

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
  requesterName: string;
  requesterEmail: string;
  documentNames: string[];
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  cachedInputTokens: number;
  estimatedCostUsd: number;
  status: 'success' | 'fallback' | 'error';
  fallbackReason: string | null;
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
  user: UserSummary;
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
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  private readonly http = inject(HttpClient);
  private readonly tokenStorageKey = 'search-agent-access-token';

  activeTab: 'analysis' | 'usage' = 'analysis';
  authMode: 'login' | 'register' = 'login';
  selectedFiles: File[] = [];
  isSubmitting = false;
  isAuthenticating = false;
  isRestoringSession = true;
  isLoadingUsage = false;
  isLoadingOpenAIDebug = false;

  authFullName = '';
  authEmail = '';
  authPassword = '';

  errorMessage = '';
  authErrorMessage = '';
  usageErrorMessage = '';
  openAIDebugErrorMessage = '';

  currentUser: UserSummary | null = null;
  analysisResult: AnalysisResponse | null = null;
  usageDashboard: UsageDashboard | null = null;
  openAIDebug: OpenAIDebugResponse | null = null;

  constructor() {
    this.restoreSession();
  }

  setAuthMode(mode: 'login' | 'register'): void {
    this.authMode = mode;
    this.authErrorMessage = '';
  }

  submitAuth(): void {
    this.authErrorMessage = '';
    this.isAuthenticating = true;

    const endpoint = this.authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
    const payload = this.authMode === 'register'
      ? { email: this.authEmail, password: this.authPassword, fullName: this.authFullName }
      : { email: this.authEmail, password: this.authPassword };

    this.http.post<AuthResponse>(endpoint, payload).subscribe({
      next: (response) => {
        this.finishAuth(response);
      },
      error: (error: HttpErrorResponse) => {
        this.authErrorMessage = typeof error.error?.detail === 'string'
          ? error.error.detail
          : 'Nie uda\u0142o si\u0119 zalogowa\u0107.';
        this.isAuthenticating = false;
      }
    });
  }

  logout(): void {
    localStorage.removeItem(this.tokenStorageKey);
    this.currentUser = null;
    this.analysisResult = null;
    this.usageDashboard = null;
    this.openAIDebug = null;
    this.selectedFiles = [];
    this.errorMessage = '';
    this.usageErrorMessage = '';
    this.openAIDebugErrorMessage = '';
    this.authPassword = '';
    this.isRestoringSession = false;
  }

  setActiveTab(tab: 'analysis' | 'usage'): void {
    this.activeTab = tab;
    if (tab === 'usage' && this.currentUser) {
      this.loadUsageDashboard();
      this.loadOpenAIDebug();
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
    if (!this.currentUser) {
      this.authErrorMessage = 'Najpierw zaloguj si\u0119 do systemu.';
      return;
    }
    if (!this.selectedFiles.length) {
      this.errorMessage = 'Wybierz co najmniej jeden dokument do analizy.';
      return;
    }

    const formData = new FormData();
    this.selectedFiles.forEach((file) => formData.append('files', file, file.name));

    this.isSubmitting = true;
    this.errorMessage = '';
    this.analysisResult = null;

    this.http.post<AnalysisResponse>('/api/analyze', formData, { headers: this.authHeaders() }).subscribe({
      next: (response) => {
        this.analysisResult = response;
        this.isSubmitting = false;
        this.loadUsageDashboard();
        this.loadOpenAIDebug();
      },
      error: (error: HttpErrorResponse) => {
        this.handleProtectedError(error, 'Nie uda\u0142o si\u0119 przeanalizowa\u0107 dokument\u00f3w.');
        this.isSubmitting = false;
      }
    });
  }

  loadUsageDashboard(): void {
    if (!this.currentUser) {
      return;
    }
    this.isLoadingUsage = true;
    this.usageErrorMessage = '';
    this.http.get<UsageDashboard>('/api/usage', { headers: this.authHeaders() }).subscribe({
      next: (dashboard) => {
        this.usageDashboard = dashboard;
        this.isLoadingUsage = false;
      },
      error: (error: HttpErrorResponse) => {
        this.handleProtectedError(error, 'Nie uda\u0142o si\u0119 pobra\u0107 raportu koszt\u00f3w.');
        this.isLoadingUsage = false;
      }
    });
  }

  loadOpenAIDebug(): void {
    if (!this.currentUser) {
      return;
    }
    this.isLoadingOpenAIDebug = true;
    this.openAIDebugErrorMessage = '';
    this.http.get<OpenAIDebugResponse>('/api/debug/openai', { headers: this.authHeaders() }).subscribe({
      next: (response) => {
        this.openAIDebug = response;
        this.isLoadingOpenAIDebug = false;
      },
      error: (error: HttpErrorResponse) => {
        this.handleProtectedError(error, 'Nie uda\u0142o si\u0119 pobra\u0107 diagnostyki OpenAI.');
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

  private restoreSession(): void {
    const token = localStorage.getItem(this.tokenStorageKey);
    if (!token) {
      this.isRestoringSession = false;
      return;
    }

    this.http.get<UserSummary>('/api/me', { headers: this.authHeaders(token) }).subscribe({
      next: (user) => {
        this.currentUser = user;
        this.isRestoringSession = false;
        this.loadUsageDashboard();
        this.loadOpenAIDebug();
      },
      error: () => {
        localStorage.removeItem(this.tokenStorageKey);
        this.isRestoringSession = false;
      }
    });
  }

  private finishAuth(response: AuthResponse): void {
    localStorage.setItem(this.tokenStorageKey, response.accessToken);
    this.currentUser = response.user;
    this.authPassword = '';
    this.authErrorMessage = '';
    this.isAuthenticating = false;
    this.isRestoringSession = false;
    this.loadUsageDashboard();
    this.loadOpenAIDebug();
  }

  private authHeaders(tokenOverride?: string): HttpHeaders {
    const token = tokenOverride ?? localStorage.getItem(this.tokenStorageKey) ?? '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  private handleProtectedError(error: HttpErrorResponse, fallbackMessage: string): void {
    if (error.status === 401) {
      this.logout();
      this.authErrorMessage = 'Sesja wygas\u0142a. Zaloguj si\u0119 ponownie.';
      return;
    }

    const detail = typeof error.error?.detail === 'string' ? error.error.detail : fallbackMessage;
    if (fallbackMessage.includes('raportu koszt')) {
      this.usageErrorMessage = detail;
      return;
    }
    if (fallbackMessage.includes('diagnostyki OpenAI')) {
      this.openAIDebugErrorMessage = detail;
      return;
    }
    this.errorMessage = detail;
  }
}