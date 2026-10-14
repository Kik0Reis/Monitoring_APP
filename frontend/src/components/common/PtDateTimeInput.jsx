import { useState } from "react";

function isoToPtDate(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

function ptDateToIso(text) {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text);
  if (!match) return "";

  const [, dd, mm, yyyy] = match;
  const date = new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  const valid =
    date.getFullYear() === Number(yyyy) &&
    date.getMonth() === Number(mm) - 1 &&
    date.getDate() === Number(dd);

  return valid ? `${yyyy}-${mm}-${dd}` : "";
}

function maskDate(raw) {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  let out = digits.slice(0, 2);
  if (digits.length > 2) out += `/${digits.slice(2, 4)}`;
  if (digits.length > 4) out += `/${digits.slice(4)}`;
  return out;
}

/* ---- time ---- */

function ptTimeToValue(text) {
  const match = /^(\d{2}):(\d{2})$/.exec(text);
  if (!match) return "";
  return Number(match[1]) < 24 && Number(match[2]) < 60 ? text : "";
}

function maskTime(raw) {
  const digits = raw.replace(/\D/g, "").slice(0, 4);
  return digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits;
}

/* ---- shared input ---- */

function MaskedInput({ value, onChange, mask, parse, format, placeholder, maxLength, className, ariaLabel }) {
  const [text, setText] = useState(() => format(value));

  // If the value is changed from outside (e.g. "Clear filters"), follow it.
  // While the person is mid-typing the parsed value stays "", same as the
  // prop, so this doesn't fight their typing.
  if ((value || "") !== parse(text)) {
    setText(format(value));
  }

  function handleChange(event) {
    const masked = mask(event.target.value);
    setText(masked);
    onChange(parse(masked));
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      autoComplete="off"
      className={className}
      placeholder={placeholder}
      maxLength={maxLength}
      aria-label={ariaLabel}
      value={text}
      onChange={handleChange}
    />
  );
}

export function DateInputPt({ value, onChange, className, ariaLabel }) {
  return (
    <MaskedInput
      value={value}
      onChange={onChange}
      mask={maskDate}
      parse={ptDateToIso}
      format={isoToPtDate}
      placeholder="dd/mm/aaaa"
      maxLength={10}
      className={className}
      ariaLabel={ariaLabel}
    />
  );
}

export function TimeInputPt({ value, onChange, className, ariaLabel }) {
  return (
    <MaskedInput
      value={value}
      onChange={onChange}
      mask={maskTime}
      parse={ptTimeToValue}
      format={(v) => v || ""}
      placeholder="hh:mm"
      maxLength={5}
      className={className}
      ariaLabel={ariaLabel}
    />
  );
}
