

let spreads_format_hot;
let allStatementIds;
let pendingChanges = [];
let highlightedRows = [];
let decimalPlaces = 2; // Default to 2 decimal places
let editedCells = new Set(); // To keep track of edited cells


function initializeFinancialStatement(data) {
    const { currentCustomerId, spreadsData, statementType, datesInStatement } = data;

    if (spreadsData.length > 0) {
        allStatementIds = Object.keys(spreadsData[0])
            .filter(key => key.startsWith('statement_'))
            .map(key => spreadsData[0][key])
            .filter(id => id != null);
    }

    displaySpreadsFormat(spreadsData, statementType, datesInStatement);
    console.log(spreadsData);
    document.getElementById('decimalPlaceSelector').addEventListener('change', function (event) {
        updateDecimalPlaces(parseInt(event.target.value));
    });
    document.getElementById('saveChangesButton').addEventListener('click', () => update_spreads_data(currentCustomerId));
}

function assignClasses(row, col) {
    className = 'font-nunito text-xs';
    if (row % 2) {
        className = className + " " + '!bg-slate-100 dark:!bg-slate-700  text-gray-500 dark:text-gray-100'; //to alternate shade the rows
    } else {
        className = className + " " + '!bg-slate-200 dark:!bg-slate-800  text-gray-500 dark:text-gray-100'; //to alternate shade the rows - darker shade
    }
    if (col > 0) {
        className = className + " " + 'htRight';
    }
    return className
}
function displaySpreadsFormat(spreads_data, statement_type, dates_in_statement) {
    const spreads_format_container = document.getElementById('spreads-table');
    // Custom number formatting function
    const formatNumber = (value) => {
        if (typeof value === 'number') {
            if (value === 0) {
                return ''; // Return empty string for zero values
            }

        }
        return value; // Return as-is if not a number
    };
    const cols_all = Object.keys(spreads_data[0]).filter((x) => {
        return x.includes('value_')
    });
    const cols = cols_all.slice(0, dates_in_statement.length)


    const dates_cols = cols.map((c) => {
        return {
            data: c,
            type: 'numeric',
            numericFormat: {
                pattern: {
                    mantissa: decimalPlaces
                },
                culture: 'en-US'
            },
            renderer: function (instance, td, row, col, prop, value, cellProperties) {
                Handsontable.renderers.NumericRenderer.apply(this, arguments);
                if (value === 0) {
                    td.textContent = '';
                }
                // Add red border to edited cells
                const cellId = `${row}-${col}`;
                if (editedCells.has(cellId)) {
                    td.style.border = '2px solid red';
                }
            }
        }
    });
    spreads_format_hot = new Handsontable(spreads_format_container, {
        data: spreads_data,
        cells: function (row, col) {
            var cellProperties = {};
            var className = " "
            if (highlightedRows.includes(row)) {
                className += ' highlighted-formula-component';
            }
            else {
                className += assignClasses(row, col);
            }
            cellProperties.className = className;
            return cellProperties;
        },
        colHeaders: ['Line Item', ...dates_in_statement],
        columns: [
            { data: 'template_label', type: 'text' }, ...dates_cols
        ],
        width: "auto",
        stretchH: "all",
        height: "700px",

        licenseKey: 'non-commercial-and-evaluation',
        afterChange: function (changes, source) {
            if (source === 'edit' || source === "CopyPaste.paste") {
                if (changes && changes.length > 0) {
                    pendingChanges = changes.map(([row, prop, oldValue, newValue]) => {
                        const rowData = this.getSourceDataAtRow(row);
                        const statementIndex = parseInt(prop.split('_')[1]) - 1;
                        const col = this.propToCol(prop);
                        if (oldValue!=newValue){

                            editedCells.add(`${row}-${col}`);
                        }
                        // spreads_format_hot.setCellMeta(row, col, 'className', 'isDirty');
                        spreads_format_hot.render();
                        return {
                            statement_id: rowData[`statement_${statementIndex + 1}`],
                            template_financial_item_id: rowData.template_financial_item_id,
                            template_financial_line_item_name: rowData.template_financial_line_item_name,
                            old_value: oldValue,
                            new_value: newValue
                        };
                    });
                    document.getElementById('saveChangesButton').disabled = false;
                    //update_spreads_data(pendingChanges,allStatementIds);
                }
            }
        },
        beforeOnCellMouseDown: function (event, coords, TD) {
            if (coords.col > 0) {
                const formula = spreads_format_hot.getSourceData()[coords.row].formula
                if (formula) {
                    const lineItemNames = extractFormulaComponents(formula);
                    highlightRows(spreads_format_hot, lineItemNames);
                    showFormulaTooltip(TD, formula);
                }
            } else {
                removeHighlights(spreads_format_hot);
                //removeFormulaTooltip();
            }
        }
    });

}


function update_spreads_data(currentCustomerId) {
    showLoadingIndicator();
    disableInteractions();
    const updatedValuesUrl = '/update_statement'

    fetch(updatedValuesUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            line_items: pendingChanges,
            multi_statement_ids: allStatementIds,
            customer_id: currentCustomerId  // Make sure this variable is set somewhere in your code
        })
    })
        .then(response => {
            if (response.redirected) {
                // If the response is a redirect, navigate to the new URL
                window.location.href = response.url;
            } else if (!response.ok) {
                throw new Error('Network response was not ok');
            }
        })
        .catch(error => {
            console.error('Error updating statement data:', error);
            hideLoadingIndicator();
            enableInteractions();

        });
}
function extractRowIdsFromFormula(formula) {
    const regex = /\b\w+_\d+\b/g;
    return formula.match(regex);
}
function extractFormulaComponents(formula) {
    // Split the formula by common operators (+, -, *, /)
    const components = formula.split(/\s*[\+\-\*\/]\s*/);

    // Trim each component and filter out any empty strings
    const trimmedComponents = components
        .map(component => component.trim())
        .filter(component => component.length > 0);

    // Log for debugging
    console.log("Formula:", formula);
    console.log("Extracted components:", trimmedComponents);

    return trimmedComponents;
}
function highlightRows(spreads_format_hot, lineItemNames) {
    // Clear previous highlights
    removeHighlights(spreads_format_hot);

    const data = spreads_format_hot.getSourceData();
    highlightedRows = data.reduce((acc, row, index) => {
        if (lineItemNames.includes(row.template_financial_line_item_name)) {
            acc.push(index);
        }
        return acc;
    }, []);
    console.log("Highlighted rows: ", highlightedRows);
    highlightedRows.forEach(row => {
        for (let col = 0; col < spreads_format_hot.countCols(); col++) {
            console.log("The cell meta for the row is: ", spreads_format_hot.getCellMeta(row, col));
            spreads_format_hot.setCellMeta(row, col, 'className',
                spreads_format_hot.getCellMeta(row, col).className + ' highlighted-formula-component');
        }
    });

    spreads_format_hot.render();
}

function removeHighlights(spreads_format_hot) {
    highlightedRows.forEach(row => {
        for (let col = 0; col < spreads_format_hot.countCols(); col++) {
            let className = spreads_format_hot.getCellMeta(row, col).className || '';
            className = className.replace('highlighted-formula-component', '').trim();
            spreads_format_hot.setCellMeta(row, col, 'className', className);
        }
    });

    highlightedRows = [];
    spreads_format_hot.render();
}

function showFormulaTooltip(cell, formula) {
    const tooltip = document.createElement('div');
    tooltip.className = 'formula-tooltip';
    tooltip.textContent = formula;
    cell.appendChild(tooltip);
}
function updateDecimalPlaces(decimalPlaces) {
    currentDecimalPlaces = decimalPlaces;

    const columnsConfig = spreads_format_hot.getSettings().columns;
    columnsConfig.forEach((column, index) => {
        if (index > 0) { // Skip the first column (template_label)
            column.numericFormat = {
                pattern: { mantissa: decimalPlaces },
                culture: 'en-US'
            };
        }
    });

    spreads_format_hot.updateSettings({
        columns: columnsConfig
    });

    spreads_format_hot.render(); // Re-render the table
}
// displaySpreadsFormat(spreads_data, statement_type, dates_in_statement);
