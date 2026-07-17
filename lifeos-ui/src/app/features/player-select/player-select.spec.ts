import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PlayerSelect } from './player-select';

describe('PlayerSelect', () => {
  let component: PlayerSelect;
  let fixture: ComponentFixture<PlayerSelect>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlayerSelect],
    }).compileComponents();

    fixture = TestBed.createComponent(PlayerSelect);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
