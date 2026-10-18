// Theme switch: remembers the choice; the page starts in the saved or system theme.
document.querySelector(".theme-toggle").addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem("theme", theme); } catch (e) {}
});

// Searchable dropdowns: a select marked data-combobox gets a text box that lists the
// options matching what is typed. The select stays the source of truth (hidden), so
// code reading its value and listening for "change" keeps working.
for (const select of document.querySelectorAll("select[data-combobox]")) {
  const listId = `${select.id}-options`;
  const input = document.createElement("input");
  Object.assign(input, { type: "search", autocomplete: "off", spellcheck: false });
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-expanded", "false");
  input.setAttribute("aria-controls", listId);
  const list = document.createElement("ul");
  Object.assign(list, { id: listId, className: "combo-list", hidden: true });
  list.setAttribute("role", "listbox");
  const wrap = document.createElement("div");
  wrap.className = "combo";
  select.after(wrap);
  wrap.append(input, list);
  select.hidden = true;
  select.tabIndex = -1;

  // The empty option ("All institutions", "Choose your institution") is the placeholder.
  const blank = () => [...select.options].find((option) => !option.value);
  const choices = () => [...select.options].filter((option) => option.value);
  const sync = () => {
    const option = select.selectedOptions[0];
    input.value = option && option.value ? option.text : "";
    input.placeholder = blank() ? blank().text : "";
  };
  let matches = [], active = -1;
  const show = (on) => { list.hidden = !on; input.setAttribute("aria-expanded", String(on)); };
  const highlight = (index) => {
    active = index;
    [...list.children].forEach((item, i) => item.classList.toggle("active", i === index));
    if (list.children[index]) {
      list.children[index].scrollIntoView({ block: "nearest" });
      input.setAttribute("aria-activedescendant", list.children[index].id);
    } else input.removeAttribute("aria-activedescendant");
  };
  const render = () => {
    const words = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    // Options can carry extra search text (data-search), such as an institution's alternate names.
    matches = choices().filter((option) => {
      const text = (option.dataset.search || option.text).toLowerCase();
      return words.every((word) => text.includes(word));
    });
    list.replaceChildren(...(matches.length ? matches.map((option, i) => {
      const item = document.createElement("li");
      Object.assign(item, { id: `${listId}-${i}`, textContent: option.text });
      item.setAttribute("role", "option");
      item.addEventListener("mousedown", (event) => { event.preventDefault(); pick(option.value); });
      return item;
    }) : [Object.assign(document.createElement("li"), { className: "combo-empty", textContent: "No match" })]));
    highlight(words.length && matches.length ? 0 : -1);
    show(true);
  };
  const pick = (value) => {
    const changed = select.value !== value;
    select.value = value;
    sync();
    show(false);
    if (changed) select.dispatchEvent(new Event("change"));
  };
  // Leaving the box keeps an exact or only match, clears on empty, and otherwise restores the choice.
  const settle = () => {
    const text = input.value.trim().toLowerCase();
    const exact = choices().find((option) => option.text.toLowerCase() === text);
    if (!text) pick("");
    else if (exact) pick(exact.value);
    else if (matches.length === 1) pick(matches[0].value);
    else { sync(); show(false); }
  };
  // Opening the box (by focus, or by clicking it again after a choice) selects its text,
  // so typing replaces the chosen name.
  const open = () => { if (list.hidden) { input.select(); render(); } };
  input.addEventListener("focus", open);
  input.addEventListener("click", open);
  input.addEventListener("input", render);
  input.addEventListener("blur", settle);
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (list.hidden) return render();
      const step = event.key === "ArrowDown" ? 1 : -1;
      if (matches.length) highlight((active + step + matches.length) % matches.length);
    } else if (event.key === "Enter") {
      if (list.hidden) return;
      event.preventDefault();
      if (matches[active]) pick(matches[active].value);
      else settle();
    } else if (event.key === "Escape" && !list.hidden) {
      event.preventDefault();
      sync();
      show(false);
    }
  });
  select.addEventListener("change", sync);
  // Options may arrive later (the form loads them), so the box follows the select.
  new MutationObserver(sync).observe(select, { childList: true });
  sync();
}

// Rankings: filter by search text and, for contestants, institution.
const search = document.getElementById("search");
const institution = document.getElementById("rankings") && document.getElementById("institution");
if (search) {
  const table = document.getElementById("rankings");
  const rows = [...table.querySelectorAll("tbody tr")];
  const empty = document.getElementById("empty");
  table.classList.add("restriped");
  const apply = () => {
    const words = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const chosen = institution ? institution.value : "";
    let shown = 0;
    for (const row of rows) {
      const visible = words.every((word) => row.dataset.search.includes(word))
        && (!chosen || row.dataset.institution === chosen);
      row.hidden = !visible;
      // Zebra stripes count only the rows that are shown.
      row.classList.toggle("alt", visible && shown % 2 === 1);
      shown += visible;
    }
    empty.hidden = shown > 0;
  };
  apply();
  search.addEventListener("input", apply);
  // The chosen institution lives in the address, so institution links and shared URLs open filtered.
  if (institution) institution.addEventListener("change", () => {
    const url = new URL(location.href);
    if (institution.value) url.searchParams.set("institution", institution.value);
    else url.searchParams.delete("institution");
    history.replaceState(null, "", url);
    apply();
  });
  const chosen = new URLSearchParams(location.search).get("institution");
  if (chosen && institution && [...institution.options].some((option) => option.value === chosen)) {
    institution.value = chosen;
    institution.dispatchEvent(new Event("change"));
  }
}

// Rating chart: tooltip on hover and keyboard focus.
const tooltip = document.querySelector(".tooltip");
for (const point of document.querySelectorAll(".chart .point")) {
  const title = point.querySelector("title");
  const show = () => {
    const [heading, detail] = point.dataset.tip.split("|");
    tooltip.replaceChildren();
    const strong = document.createElement("strong");
    strong.textContent = heading;
    tooltip.append(strong, detail);
    const box = point.getBoundingClientRect();
    tooltip.style.left = `${box.left + box.width / 2}px`;
    tooltip.style.top = `${box.top}px`;
    tooltip.hidden = false;
    if (title) title.remove();  // the custom tooltip replaces the browser's
  };
  const hide = () => { tooltip.hidden = true; };
  point.addEventListener("mouseenter", show);
  point.addEventListener("focus", show);
  point.addEventListener("mouseleave", hide);
  point.addEventListener("blur", hide);
}

// Team names: show the members on hover and focus. The card stays open while the
// pointer moves onto it, so its members' profile links can be clicked.
let hideTimer = null;
const hideCard = () => { tooltip.hidden = true; tooltip.classList.remove("card"); };
const hideCardSoon = () => { clearTimeout(hideTimer); hideTimer = setTimeout(hideCard, 250); };
const keepCard = () => clearTimeout(hideTimer);
tooltip.addEventListener("mouseenter", () => { if (tooltip.classList.contains("card")) keepCard(); });
tooltip.addEventListener("mouseleave", () => { if (tooltip.classList.contains("card")) hideCardSoon(); });
for (const label of document.querySelectorAll(".team-label")) {
  const members = label.querySelector(".team-members");
  const show = () => {
    keepCard();
    tooltip.innerHTML = members.innerHTML;
    tooltip.classList.add("card");
    const box = label.getBoundingClientRect();
    tooltip.style.left = `${box.left + box.width / 2}px`;
    tooltip.style.top = `${box.top}px`;
    tooltip.hidden = false;
  };
  label.addEventListener("mouseenter", show);
  label.addEventListener("focus", show);
  label.addEventListener("mouseleave", hideCardSoon);
  label.addEventListener("blur", hideCardSoon);  // late enough for a tap on a member link to land
}
document.addEventListener("keydown", (event) => { if (event.key === "Escape") hideCard(); });
