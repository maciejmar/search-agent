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

  readonly fallbackStandings: StandingRow[] = [
    { rank: 1, team: 'Hiszpania', matches: 3, wins: 2, draws: 1, losses: 0, goalsFor: 5, goalsAgainst: 0, goalDiff: 5, points: 7 },
    { rank: 2, team: 'Republika Zielonego Przyladka', matches: 3, wins: 0, draws: 3, losses: 0, goalsFor: 2, goalsAgainst: 2, goalDiff: 0, points: 3 },
    { rank: 3, team: 'Urugwaj', matches: 3, wins: 0, draws: 2, losses: 1, goalsFor: 3, goalsAgainst: 4, goalDiff: -1, points: 2 },
    { rank: 4, team: 'Arabia Saudyjska', matches: 3, wins: 0, draws: 2, losses: 1, goalsFor: 1, goalsAgainst: 5, goalDiff: -4, points: 2 }
  ];

  groupName = 'Grupa H';
  standings = this.fallbackStandings;
  isLoading = true;
  loadError = '';

  constructor() {
    this.http.get<StandingsResponse>('/api/standings').subscribe({
      next: (response) => {
        this.groupName = response.group;
        this.standings = response.standings;
        this.isLoading = false;
      },
      error: () => {
        this.loadError = 'Backend jest niedostepny. Wyswietlam dane lokalne.';
        this.isLoading = false;
      }
    });
  }
}
