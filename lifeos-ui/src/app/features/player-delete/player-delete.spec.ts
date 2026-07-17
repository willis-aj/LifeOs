import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PlayerDelete } from './player-delete';

describe('PlayerDelete', () => {
  let component: PlayerDelete;
  let fixture: ComponentFixture<PlayerDelete>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlayerDelete],
    }).compileComponents();

    fixture = TestBed.createComponent(PlayerDelete);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
