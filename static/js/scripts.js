$(document).ready(function() {
    let fullData = []; // Store the full dataset here

    function disableOtherInputs(activeInputId) {
        $('#proteinId, #proteinName, #proteomeId, #organismName').not(activeInputId).prop('disabled', true);
    }

    function enableAllInputs() {
        $('#proteinId, #proteinName, #proteomeId, #organismName').prop('disabled', false);
    }

    function resetForm() {
        $('#searchForm')[0].reset();
        $('#results').empty();
        $('#proteomeSelectDivFromSearch').hide();
        enableAllInputs();
    }

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function showWaitingModal() {
        $('#waitingModalCustom').css('display', 'flex');
    }

    function hideWaitingModal() {
        $('#waitingModalCustom').css('display', 'none');
    }

    $('#proteinId').on('input', function() {
        disableOtherInputs('#proteinId');
    });

    $('#proteinName').on('input', debounce(function() {
        disableOtherInputs('#proteinName');
        $('#proteinName').autocomplete({
            source: function(request, response) {
                $.ajax({
                    url: '/suggest_protein',
                    type: 'GET',
                    data: { query: request.term },
                    success: function(data) {
                        response(data);
                    },
                    error: function() {
                        response([]);
                    }
                });
            },
            select: function(event, ui) {
                $('#proteinName').val(ui.item.value);
                // Fetch proteome data based on selected protein name
                $.ajax({
                    url: '/get_proteome_data_by_protein_name',
                    type: 'GET',
                    data: { protein_name: ui.item.value },
                    success: function(data) {
                        let options = '<option value="">Select a proteome ID or organism name</option>';
                        let uniqueOptions = new Set(); // Use a Set to ensure unique options
                        if (data.length > 0) {
                            data.forEach(item => {
                                const optionText = `${item.proteome_id} - ${item.organism_name}`;
                                if (!uniqueOptions.has(optionText)) {
                                    options += `<option value="${item.id}">${optionText}</option>`;
                                    uniqueOptions.add(optionText);
                                }
                            });
                        }
                        $('#proteomeSelectFromSearch').html(options);
                        $('#proteomeSelectDivFromSearch').show();
                    },
                    error: function(err) {
                        $('#proteomeSelectFromSearch').html('<option value="">Error fetching data</option>');
                    }
                });
            }
        });
    }, 300));

    $('#proteomeId').on('input', function() {
        disableOtherInputs('#proteomeId');
    });

    $('#organismName').on('input', debounce(function() {
        disableOtherInputs('#organismName');
        $('#organismName').autocomplete({
            source: function(request, response) {
                $.ajax({
                    url: '/suggest_proteome_organism',
                    type: 'GET',
                    data: { query: request.term },
                    success: function(data) {
                        response(data);
                    },
                    error: function() {
                        response([]);
                    }
                });
            },
            select: function(event, ui) {
                $('#organismName').val(ui.item.value);
                $('#searchForm').submit();
            }
        });
    }, 300));

    $('#searchForm').on('submit', function(e) {
        e.preventDefault();
        showWaitingModal();
        let proteinId = $('#proteinId').val();
        let proteinName = $('#proteinName').val();
        let proteomeId = $('#proteomeId').val();
        let organismName = $('#organismName').val();
        let proteomeSelectFromSearch = $('#proteomeSelectFromSearch').val();
    
        let url = '';
        let data = {};
    
        if (proteinId) {
            url = '/search_protein';
            data = { protein_id: proteinId };
        } else if (proteinName) {
            url = '/search_protein';
            data = { protein_name: proteinName };
            if (proteomeSelectFromSearch) {
                data.proteome_id = proteomeSelectFromSearch;
            }
        } else if (proteomeId) {
            url = '/search_proteome_organism';
            data = { proteome_id: proteomeId };
        } else if (organismName) {
            url = '/search_proteome_organism';
            data = { organism_name: organismName };
        }
    
        $.ajax({
            url: url,
            type: 'GET',
            data: data,
            success: function(data) {
                fullData = data; // Store the full dataset
                let results = '<table class="table table-bordered">';
                results += '<thead><tr>';
                results += '<th>Protein ID</th><th>Protein Name</th><th>Predicted Antigenic Score</th>';
                results += '<th>Predicted Antigenic Probability</th><th>Predicted Signal Peptide</th><th>Number of TMHS</th>';
                results += '<th>Localizations</th><th>Vaccine Candidate Probability</th><th>Experimentally Validated Antigen</th>';
                results += '<th>PMID</th><th>Submission ID IEDB</th><th>DOI</th>';
                results += '</tr></thead><tbody>';
                
                if (data.length > 0) {
                    const displayData = data.slice(0, 100); // Display only the first 100 results
                    displayData.forEach(item => {
                        results += '<tr>';
                        results += `<td>${item.protein_id}</td><td>${item.protein_name}</td>`;
                        results += `<td>${item.predicted_antigenic_score}</td><td>${item.predicted_antigenic_probability}</td>`;
                        results += `<td>${item.predicted_signal_peptide}</td><td>${item.number_of_tmhs}</td>`;
                        results += `<td>${item.localizations}</td><td>${item.vaccine_candidate_probability}</td>`;
                        results += `<td>${item.experimentally_validated_antigen || 'NA'}</td><td>${item.pmid || 'NA'}</td>`;
                        results += `<td>${item.submission_id_iedb || 'NA'}</td><td>${item.doi || 'NA'}</td>`;
                        results += '</tr>';
                    });
                } else {
                    results += '<tr><td colspan="12">No results found.</td></tr>';
                }
                results += '</tbody></table>';
                
                $('#searchFullScreenResults').html(results);
                $('#searchFullScreenDiv').show();
                $('#searchFullScreenDiv').scrollTop(0); // Scroll to top of the search results div
                $('html, body').animate({ scrollTop: $('#searchFullScreenDiv').offset().top }, 'fast'); // Smooth scroll to div
                enableAllInputs();
                hideWaitingModal();
            },
            error: function(err) {
                $('#searchFullScreenResults').html('<p>Error fetching results.</p>');
                enableAllInputs();
                hideWaitingModal();
            }
        });
    });
   
    $('#resetButton').on('click', function() {
        resetForm();
    });

    $('#organismType').on('change', function() {
        let organismType = $(this).val();

        if (!organismType) {
            $('#proteomeResults').empty();
            $('#proteomeSelectDiv').hide();
            return;
        }

        showWaitingModal(); // Show the waiting modal when the request starts

        $.ajax({
            url: '/get_proteome_data',
            type: 'GET',
            data: { organism_type: organismType },
            success: function(data) {
                fullData = data; // Store the full dataset
                let options = '<option value="">Select a proteome ID or organism name</option>';
                if (data.length > 0) {
                    data.forEach(item => {
                        options += `<option value="${item.id}">${item.proteome_id} - ${item.organism_name}</option>`;
                    });
                }
                $('#proteomeSelect').html(options);
                $('#proteomeSelectDiv').show();
                hideWaitingModal(); // Hide the waiting modal when the request completes successfully
            },
            error: function(err) {
                $('#proteomeResults').html('<p>Error fetching results.</p>');
                hideWaitingModal(); // Hide the waiting modal if there is an error
            }
        });
    });

    $('#proteomeSelect').on('change', function() {
        let fileId = $(this).val();
    
        if (!fileId) {
            $('#proteomeResults').empty();
            return;
        }
    
        showWaitingModal();

        $.ajax({
            url: '/get_protein_data',
            type: 'GET',
            data: { file_id: fileId },
            success: function(data) {
                fullData = data; // Store the full dataset
                let results = '<table class="table table-bordered">';
                results += '<thead><tr>';
                results += '<th>Protein ID</th><th>Protein Name</th><th>Predicted Antigenic Score</th>';
                results += '<th>Predicted Antigenic Probability</th><th>Predicted Signal Peptide</th><th>Number of TMHS</th>';
                results += '<th>Localizations</th><th>Vaccine Candidate Probability</th><th>Experimentally Validated Antigen</th>';
                results += '<th>PMID</th><th>Submission ID IEDB</th><th>DOI</th>';
                results += '</tr></thead><tbody>';
    
                if (data.length > 0) {
                    const displayData = data.slice(0, 100); // Display only the first 100 results
                    displayData.forEach(item => {
                        results += '<tr>';
                        results += `<td>${item.protein_id}</td><td>${item.protein_name}</td>`;
                        results += `<td>${item.predicted_antigenic_score}</td><td>${item.predicted_antigenic_probability}</td>`;
                        results += `<td>${item.predicted_signal_peptide}</td><td>${item.number_of_tmhs}</td>`;
                        results += `<td>${item.localizations}</td><td>${item.vaccine_candidate_probability}</td>`;
                        results += `<td>${item.experimentally_validated_antigen || 'NA'}</td><td>${item.pmid || 'NA'}</td>`;
                        results += `<td>${item.submission_id_iedb || 'NA'}</td><td>${item.doi || 'NA'}</td>`;
                        results += '</tr>';
                    });
                } else {
                    results += '<tr><td colspan="12">No results found.</td></tr>';
                }
                results += '</tbody></table>';
    
                $('#fullScreenResults').html(results);
                $('#fullScreenDiv').show();
                $('#fullScreenDiv').scrollTop(0); // Scroll to top of the full screen div
                $('html, body').animate({ scrollTop: $('#fullScreenDiv').offset().top }, 'fast'); // Smooth scroll to div
                hideWaitingModal();
            },
            error: function(err) {
                $('#fullScreenResults').html('<p>Error fetching proteins.</p>');
                hideWaitingModal();
            }
        });
    });
    
    $('#closeFullScreenDiv').on('click', function() {
        $('#fullScreenDiv').hide();
    });

    $('#closeSearchFullScreenDiv').on('click', function() {
        $('#searchFullScreenDiv').hide();
    });

    // Function to filter data based on user selection
    function filterData(data, vaccineFilter, antigenFilter) {
        return data.filter(function(item) {
            return (vaccineFilter === "" || item["vaccine_candidate_probability"] === vaccineFilter) &&
                   (antigenFilter === "" || item["experimentally_validated_antigen"] === antigenFilter);
        }).map(function(item) {
            return {
                protein_id: item.protein_id,
                protein_name: item.protein_name,
                predicted_antigenic_score: item.predicted_antigenic_score,
                predicted_antigenic_probability: item.predicted_antigenic_probability,
                predicted_signal_peptide: item.predicted_signal_peptide,
                number_of_tmhs: item.number_of_tmhs,
                localizations: item.localizations,
                vaccine_candidate_probability: item.vaccine_candidate_probability,
                experimentally_validated_antigen: item.experimentally_validated_antigen || 'NA',
                pmid: item.pmid || 'NA',
                submission_id_iedb: item.submission_id_iedb || 'NA',
                doi: item.doi || 'NA'
            };
        });
    }
    

    // Function to download JSON data as an Excel file
    function downloadExcel(data, filename) {
        var processedData = data.map(function(item) {
            return {
                'Protein ID': item.protein_id,
                'Protein Name': item.protein_name,
                'Predicted Antigenic Score': item.predicted_antigenic_score,
                'Predicted Antigenic Probability': item.predicted_antigenic_probability,
                'Predicted Signal Peptide': item.predicted_signal_peptide,
                'Number of TMHS': item.number_of_tmhs,
                'Localizations': item.localizations,
                'Vaccine Candidate Probability': item.vaccine_candidate_probability,
                'Experimentally Validated Antigen': item.experimentally_validated_antigen || 'NA',
                'PMID': item.pmid || 'NA',
                'Submission ID IEDB': item.submission_id_iedb || 'NA',
                'DOI': item.doi || 'NA'
            };
        });
    
        var ws = XLSX.utils.json_to_sheet(processedData);
        var wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Results");
        XLSX.writeFile(wb, filename);
    }
    
    // Download results for full screen div
    $('#downloadFullScreenResults').on('click', function() {
        var vaccineFilter = $('#vaccineFilter').val();
        var antigenFilter = $('#antigenFilter').val();
        var filteredData = filterData(fullData, vaccineFilter, antigenFilter);
        if (filteredData.length === 0) {
            alert('No data available for the selected filter criteria.');
            return;
        }
        downloadExcel(filteredData, 'proteome_results.xlsx');
    });
    
    $('#downloadSearchFullScreenResults').on('click', function() {
        var vaccineFilter = $('#searchVaccineFilter').val();
        var antigenFilter = $('#searchAntigenFilter').val();
        var filteredData = filterData(fullData, vaccineFilter, antigenFilter);
        if (filteredData.length === 0) {
            alert('No data available for the selected filter criteria.');
            return;
        }
        downloadExcel(filteredData, 'search_results.xlsx');
    });
});
