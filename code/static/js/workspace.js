document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("query-form");
    if (!form) return;

    const runButton = form.querySelector("button[type=submit]");
    const banner = document.getElementById("status-banner");
    const tabs = document.querySelectorAll(".results-panel .tab");
    const panels = document.querySelectorAll(".results-panel .tab-panel");

    function activateTab(name) {
        tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
        panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === name));
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => activateTab(tab.dataset.tab));
    });

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        })[c]);
    }

    function renderTable(columns, rows) {
        if (!rows.length) {
            return '<p class="placeholder">No rows.</p>';
        }
        const head = "<tr>" + columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("") + "</tr>";
        const body = rows
            .map((row) => "<tr>" + row.map((v) => `<td>${v === null ? "NULL" : escapeHtml(v)}</td>`).join("") + "</tr>")
            .join("");
        return `<div class="table-scroll"><table class="sample-table"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
    }

    function setBanner(status, message) {
        banner.hidden = false;
        banner.textContent = message;
        banner.className = "status-banner status-" + status;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const query = form.query.value;
        const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;

        runButton.disabled = true;
        runButton.textContent = "Running...";
        banner.hidden = true;

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrfToken,
                },
                body: "query=" + encodeURIComponent(query),
            });
            const result = await response.json();

            document.querySelector('[data-panel="output"]').innerHTML = result.columns
                ? renderTable(result.columns, result.rows)
                : '<p class="placeholder">No output.</p>';
            document.querySelector('[data-panel="expected"]').innerHTML = result.expected_columns
                ? renderTable(result.expected_columns, result.expected_rows)
                : '<p class="placeholder">Not available.</p>';
            document.querySelector('[data-panel="errors"]').innerHTML = result.error
                ? `<pre class="error">${escapeHtml(result.error)}</pre>`
                : '<p class="placeholder">No errors.</p>';

            if (result.status === "correct") {
                setBanner("correct", "Correct!");
                activateTab("output");
            } else if (result.status === "incorrect") {
                setBanner("incorrect", "Not quite — compare Your Output with Expected Output.");
                activateTab("output");
            } else {
                setBanner("error", "Error: " + result.error);
                activateTab("errors");
            }
        } catch (err) {
            setBanner("error", "Something went wrong running your query.");
        } finally {
            runButton.disabled = false;
            runButton.textContent = "Run";
        }
    });
});
