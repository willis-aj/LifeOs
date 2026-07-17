import { Component } from '@angular/core';

import { NavShell } from './shared/nav-shell/nav-shell';

@Component({
  selector: 'app-root',
  imports: [NavShell],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
