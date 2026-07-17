import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BacklogView } from './backlog-view';

describe('BacklogView', () => {
  let component: BacklogView;
  let fixture: ComponentFixture<BacklogView>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BacklogView],
    }).compileComponents();

    fixture = TestBed.createComponent(BacklogView);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
