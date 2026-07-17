import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NavShell } from './nav-shell';

describe('NavShell', () => {
  let component: NavShell;
  let fixture: ComponentFixture<NavShell>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavShell],
    }).compileComponents();

    fixture = TestBed.createComponent(NavShell);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
