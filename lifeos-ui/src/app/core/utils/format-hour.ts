/** Formats a 24-hour integer (0-23) as 12-hour clock text with AM/PM,
 * e.g. 0 -> "12:00 AM", 13 -> "1:00 PM". Backend storage stays 24-hour;
 * this is purely a display concern shared by every view that shows a
 * scheduled hour. */
export function formatHour(hour: number): string {
  const period = hour < 12 ? 'AM' : 'PM';
  let display = hour % 12;
  if (display === 0) {
    display = 12;
  }
  return `${display}:00 ${period}`;
}
