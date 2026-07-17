import { TestBed } from '@angular/core/testing';

import { Notify } from './notify';

describe('Notify', () => {
  let service: Notify;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Notify);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
