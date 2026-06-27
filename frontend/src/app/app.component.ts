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

interface AnalysisResponse {
  documents: UploadedDocument[];
  parties: PartyResult[];
  globalIssues: GlobalIssue[];
  summary: string;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  private readonly http = inject(HttpClient);

  selectedFiles: File[] = [];
  isSubmitting = false;
  errorMessage = '';
  analysisResult: AnalysisResponse | null = null;

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
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage = typeof error.error?.detail === 'string'
          ? error.error.detail
          : 'Nie udalo sie przeanalizowac dokumentow.';
        this.isSubmitting = false;
      }
    });
  }

  trackParty(_: number, party: PartyResult): string {
    return party.normalizedName;
  }
}
