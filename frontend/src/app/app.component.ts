import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject } from '@angular/core';

interface StandingRow {
  rank: number;
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
}

interface StandingsResponse {
  group: string;
  standings: StandingRow[];
}

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  private readonly http = inject(HttpClient);

  groupName = 'Tabela';
  standings: StandingRow[] = [];
  isLoading = true;
  loadError = '';

  constructor() {
    this.http.get<StandingsResponse>('/api/standings').subscribe({
      next: (response) => {
        this.groupName = response.group || 'Tabela';
        this.standings = response.standings;
        this.isLoading = false;
      },
      error: () => {
        this.loadError = 'Nie udalo sie pobrac danych z backendu.';
        this.isLoading = false;
      }
    });
  }
}
