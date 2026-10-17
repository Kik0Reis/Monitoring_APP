import { useEffect, useRef } from "react";
import flatpickr from "flatpickr";
import { Portuguese } from "flatpickr/dist/esm/l10n/pt.js";

import "flatpickr/dist/flatpickr.min.css";
import "flatpickr/dist/themes/dark.css";


// date or time picker that is always in portuguese (dd/mm/aaaa and 24 hour time) whatever the browser language is
// mode date: value is yyyy-mm-dd, mode time: value is hh:mm, an empty string means nothing selected
function PickerInput({ mode, value, onChange, className, ariaLabel }) {
  const inputRef = useRef(null);
  const pickerRef = useRef(null);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    valueRef.current = value;
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    const isDate = mode === "date";

    const picker = flatpickr(inputRef.current, {
      locale: Portuguese,
      allowInput: true,
      defaultDate: valueRef.current || undefined,
      altInputClass: className,
      ...(isDate
        ? { dateFormat: "Y-m-d", altInput: true, altFormat: "d/m/Y" }
        : { enableTime: true, noCalendar: true, dateFormat: "H:i", time_24hr: true }),
      onChange: (_dates, dateString) => onChangeRef.current(dateString),
    });

    // in date mode the visible field is the copy made by flatpickr, not our input
    const visible = picker.altInput ?? picker.input;
    visible.setAttribute("aria-label", ariaLabel);
    visible.setAttribute("autocomplete", "off");

    pickerRef.current = picker;
    return () => picker.destroy();
  }, [mode, className, ariaLabel]);

  // follows changes made from outside, for example the clear filters button
  useEffect(() => {
    const picker = pickerRef.current;
    if (picker && picker.input.value !== (value || "")) {
      picker.setDate(value || null, false);
    }
  }, [value]);

  // in date mode flatpickr shows its own copy (dd/mm/aaaa) and this input only holds the yyyy-mm-dd value, so it is hidden
  // in time mode this input is the visible field
  return (
    <input
      ref={inputRef}
      type={mode === "date" ? "hidden" : "text"}
      className={className}
      placeholder={mode === "date" ? "dd/mm/aaaa" : "hh:mm"}
    />
  );
}

export default PickerInput;
