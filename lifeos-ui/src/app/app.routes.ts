import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'players' },
  {
    path: 'players',
    loadComponent: () => import('./features/player-select/player-select').then((m) => m.PlayerSelect),
  },
  {
    path: 'home',
    loadComponent: () => import('./features/home/home').then((m) => m.Home),
  },
  {
    path: 'day',
    loadComponent: () => import('./features/day-view/day-view').then((m) => m.DayView),
  },
  {
    path: 'month',
    loadComponent: () => import('./features/month-view/month-view').then((m) => m.MonthView),
  },
  {
    path: 'backlog',
    loadComponent: () => import('./features/backlog-view/backlog-view').then((m) => m.BacklogView),
  },
  {
    path: 'goals',
    loadComponent: () => import('./features/goals/goals').then((m) => m.Goals),
  },
  {
    path: 'modes',
    loadComponent: () => import('./features/modes/modes').then((m) => m.Modes),
  },
  {
    path: 'self-care',
    loadComponent: () => import('./features/self-care/self-care').then((m) => m.SelfCare),
  },
  {
    path: 'settings',
    loadComponent: () => import('./features/settings/settings').then((m) => m.Settings),
  },
  { path: '**', redirectTo: 'players' },
];
