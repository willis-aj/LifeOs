import { TestBed } from '@angular/core/testing';

import { PlayerContext } from './player-context';

describe('PlayerContext', () => {
  let service: PlayerContext;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PlayerContext);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
