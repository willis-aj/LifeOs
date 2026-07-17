import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

/** A small modal form for entering a new player's name. Closes with the
 * trimmed name string, or undefined if cancelled. */
@Component({
  selector: 'app-player-create',
  imports: [FormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule],
  templateUrl: './player-create.html',
  styleUrl: './player-create.scss',
})
export class PlayerCreate {
  name = '';

  constructor(private readonly dialogRef: MatDialogRef<PlayerCreate, string>) {}

  submit(): void {
    const trimmed = this.name.trim();
    if (!trimmed) {
      return;
    }
    this.dialogRef.close(trimmed);
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
