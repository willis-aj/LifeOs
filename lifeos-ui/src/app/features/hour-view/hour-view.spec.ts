import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HourView } from './hour-view';

describe('HourView', () => {
  let component: HourView;
  let fixture: ComponentFixture<HourView>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HourView],
    }).compileComponents();

    fixture = TestBed.createComponent(HourView);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
