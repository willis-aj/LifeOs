import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PlayerCreate } from './player-create';

describe('PlayerCreate', () => {
  let component: PlayerCreate;
  let fixture: ComponentFixture<PlayerCreate>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlayerCreate],
    }).compileComponents();

    fixture = TestBed.createComponent(PlayerCreate);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
