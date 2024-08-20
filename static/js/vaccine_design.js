// Toggle custom input for "Other" options and make it required
function toggleCustomInput(selectId, inputId) {
    const selectElem = document.getElementById(selectId);
    const inputElem = document.getElementById(inputId);

    selectElem.addEventListener('change', function () {
        if (this.value === 'other') {
            inputElem.classList.remove('d-none');
            inputElem.required = true;
        } else {
            inputElem.classList.add('d-none');
            inputElem.required = false;
        }
    });
}

toggleCustomInput('adjuvant_linker', 'adjuvant_linker_other');
toggleCustomInput('adjuvant', 'adjuvant_other');
toggleCustomInput('his_tag', 'his_tag_other');

function toggleLinkerRequired(epitopeTextareaId, linkerSelectId, linkerInputId) {
    const epitopeTextarea = document.getElementById(epitopeTextareaId);
    const linkerSelect = document.getElementById(linkerSelectId);
    const linkerInput = document.getElementById(linkerInputId);

    epitopeTextarea.addEventListener('input', function () {
        if (epitopeTextarea.value.trim() !== '') {
            linkerSelect.disabled = false;
            linkerSelect.required = true;
        } else {
            linkerSelect.disabled = true;
            linkerSelect.required = false;
            linkerInput.classList.add('d-none');
            linkerInput.required = false;
        }
    });

    linkerSelect.addEventListener('change', function () {
        if (this.value === 'other') {
            linkerInput.classList.remove('d-none');
            linkerInput.required = true;
        } else {
            linkerInput.classList.add('d-none');
            linkerInput.required = false;
        }
    });
}

toggleLinkerRequired('b_cell_epitope', 'b_cell_linker', 'b_cell_linker_other');
toggleLinkerRequired('mhc_class_i_epitope', 'mhc_class_i_linker', 'mhc_class_i_linker_other');
toggleLinkerRequired('mhc_class_ii_epitope', 'mhc_class_ii_linker', 'mhc_class_ii_linker_other');


    // Prevent sending empty fields to the server
    document.getElementById('vaccineForm').addEventListener('submit', function (event) {
        const elements = this.elements;
        for (let i = 0; i < elements.length; i++) {
            if (elements[i].value === '') {
                elements[i].disabled = true;
            }
        }
    });

    function copyToClipboard(elementId) {
        var text = document.getElementById(elementId).innerText;
        navigator.clipboard.writeText(text).then(function() {
            alert('Result copied to clipboard!');
        }, function(err) {
            console.error('Could not copy text: ', err);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('downloadDocx').addEventListener('click', async () => {

            const { Document, Packer, Paragraph, TextRun } = docx;
    
            const results = document.getElementsByClassName('result-text');
            const vaccineName = document.getElementById('downloadDocx').getAttribute('data-vaccine-name');
            const filename = vaccineName + "_results.docx";
    
            // Helper function to convert RGB to HEX
            function rgbToHex(rgb) {
                const [r, g, b] = rgb.match(/\d+/g).map(Number);
                return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase()}`;
            }
    
            // Create a new DOCX document
            const doc = new Document({
                sections: [
                    {
                        properties: {},
                        children: Array.from(results).map((resultElement, index) => {
                            // Extract content and styles
                            const children = Array.from(resultElement.children).map(child => {
                                if (child.nodeName === 'SPAN') {
                                    const color = window.getComputedStyle(child).color;
                                    const hexColor = rgbToHex(color);
                                    return new TextRun({
                                        text: child.textContent,
                                        color: hexColor
                                    });
                                }
                                return new TextRun({ text: child.textContent });
                            });
    
                            // Add the combination number and vaccine name
                            const combinationText = `Combination ${index + 1} For ${vaccineName}\n`;
    
                            return new Paragraph({
                                children: [
                                    new TextRun({
                                        text: combinationText,
                                        bold: true,
                                        size: 32, // Adjust font size if needed
                                    }),
                                    ...children
                                ],
                                spacing: {
                                    after: 200
                                }
                            });
                        }),
                    },
                ],
            });
    
            // Generate DOCX file
            const blob = await Packer.toBlob(doc);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        });
    });
    