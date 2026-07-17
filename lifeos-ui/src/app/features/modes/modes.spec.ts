import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Modes } from './modes';

describe('Modes', () => {
  let component: Modes;
  let fixture: ComponentFixture<Modes>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Modes],
    }).compileComponents();

    fixture = TestBed.createComponent(Modes);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
