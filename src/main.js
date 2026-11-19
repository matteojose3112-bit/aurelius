import { getDatasetStats, parseCSV, searchRows } from "./csv.js";
import "./styles.css";

const elements = {
  dropZone: document.querySelector("#drop-zone"),
  fileInput: document.querySelector("#file-input"),
  dataPanel: document.querySelector("#data-panel"),
  fileName: document.querySelector("#file-name"),
  rowCount: document.querySelector("#row-count"),
  columnCount: document.querySelector("#column-count"),
  emptyCount: document.querySelector("#empty-count"),
  searchInput: document.querySelector("#search-input"),
  resultCount: document.querySelector("#result-count"),
  tableHead: document.querySelector("#table-head"),
  tableBody: document.querySelector("#table-body"),
  tableFootnote: document.querySelector("#table-footnote"),
  clearButton: document.querySelector("#clear-button"),
  errorMessage: document.querySelector("#error-message"),
};

const state = { headers: [], rows: [], fileName: "" };
const PREVIEW_LIMIT = 100;

elements.fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files ?? [];
  if (file) loadFile(file);
});

elements.dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  elements.dropZone.classList.add("is-dragging");
});

elements.dropZone.addEventListener("dragleave", () => {
  elements.dropZone.classList.remove("is-dragging");
});

elements.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  elements.dropZone.classList.remove("is-dragging");
  const [file] = event.dataTransfer.files ?? [];
  if (file) loadFile(file);
});

elements.searchInput.addEventListener("input", renderTable);
elements.clearButton.addEventListener("click", resetWorkspace);

async function loadFile(file) {
  hideError();

  if (!file.name.toLowerCase().endsWith(".csv") && file.type !== "text/csv") {
    showError("Please choose a CSV file.");
    return;
  }

  try {
    const content = await file.text();
    const dataset = parseCSV(content);

    if (!dataset.headers.length) {
      showError("This file appears to be empty.");
      return;
    }

    state.headers = dataset.headers;
    state.rows = dataset.rows;
    state.fileName = file.name;
    elements.fileName.textContent = file.name;
    elements.dropZone.hidden = true;
    elements.dataPanel.hidden = false;

    const stats = getDatasetStats(state.rows, state.headers.length);
    elements.rowCount.textContent = stats.rowCount.toLocaleString();
    elements.columnCount.textContent = stats.columnCount.toLocaleString();
    elements.emptyCount.textContent = stats.emptyCells.toLocaleString();
    elements.searchInput.value = "";
    renderTable();
  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to read this CSV file.");
  }
}

function renderTable() {
  const filteredRows = searchRows(state.rows, elements.searchInput.value);
  const visibleRows = filteredRows.slice(0, PREVIEW_LIMIT);

  elements.tableHead.replaceChildren();
  elements.tableBody.replaceChildren();

  const headerRow = document.createElement("tr");
  for (const header of state.headers) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = header;
    headerRow.append(cell);
  }
  elements.tableHead.append(headerRow);

  for (const row of visibleRows) {
    const tableRow = document.createElement("tr");
    for (const value of row) {
      const cell = document.createElement("td");
      cell.textContent = value;
      tableRow.append(cell);
    }
    elements.tableBody.append(tableRow);
  }

  elements.resultCount.textContent = `${filteredRows.length.toLocaleString()} records`;
  elements.tableFootnote.textContent =
    filteredRows.length > PREVIEW_LIMIT
      ? `Showing the first ${PREVIEW_LIMIT} matching rows.`
      : `Showing all ${filteredRows.length} matching rows.`;
}

function resetWorkspace() {
  state.headers = [];
  state.rows = [];
  state.fileName = "";
  elements.fileInput.value = "";
  elements.searchInput.value = "";
  elements.dataPanel.hidden = true;
  elements.dropZone.hidden = false;
  hideError();
}

function showError(message) {
  elements.errorMessage.textContent = message;
  elements.errorMessage.hidden = false;
}

function hideError() {
  elements.errorMessage.hidden = true;
  elements.errorMessage.textContent = "";
}
