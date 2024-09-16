document.addEventListener('DOMContentLoaded', function () {

    const contentContainer = document.querySelector('#ratingView');  // Adjust this selector to match your content container

    if (!contentContainer) {
        console.error('Content container not found');
        return;
    }

    document.addEventListener('click', function (e) {
        console.log('Click event triggered on content container');
        console.log('Clicked element:', e.target);

        let targetButton = e.target.closest('button');
        if (!targetButton) {
            console.log('No button found in the click path');
            return;
        }


        if (targetButton.classList.contains('edit-btn')) {
            handleEditClick(targetButton);
        } else if (targetButton.classList.contains('save-btn')) {
            handleSaveClick(targetButton);
        }
    });

    function handleEditClick(editButton) {
        const factorId = editButton.getAttribute('data-factor-id');
        console.log('Editing factor:', factorId);

        const valueSpan = document.querySelector(`.factor-value[data-factor-id="${factorId}"]`);
        const selectField = document.querySelector(`.factor-input[data-factor-id="${factorId}"]`);

        if (!valueSpan || !selectField) {
            console.error('Value span or select field not found for factor:', factorId);
            return;
        }

        valueSpan.classList.add('hidden');
        selectField.classList.remove('hidden');
        selectField.focus();

        // Change edit button to save button
        editButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
        `;
        editButton.classList.add('save-btn');
        editButton.classList.remove('edit-btn');
    }

    function handleSaveClick(saveButton) {
        const factorId = saveButton.getAttribute('data-factor-id');
        console.log('Saving factor:', factorId);

        const selectField = document.querySelector(`.factor-input[data-factor-id="${factorId}"]`);
        const valueSpan = document.querySelector(`.factor-value[data-factor-id="${factorId}"]`);

        if (!selectField || !valueSpan) {
            console.error('Select field or value span not found for factor:', factorId);
            return;
        }


        // Send AJAX request to update the value
        fetch('/api/update_factor_value', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                factor_id: factorId,
                new_value: selectField.value
            }),
        }).then(response => {
            console.log('Received response:', response);
            return response.json();
        }).then(data => {
            console.log('Parsed response data:', data);
            if (data.success) {
                console.log('Update successful');
                valueSpan.textContent = selectField.value;
                const scoreSpan = document.querySelector(`.factor-score[data-factor-id="${factorId}"]`);
                if (scoreSpan) {
                    scoreSpan.textContent = data.new_score
                }
                // Update derived values
                for (let derivedFactor of data.updated_derived_factors) {
                    const derivedValueSpan = document.querySelector(`.factor-value[data-factor-id="${derivedFactor.id}"]`);
                    const derivedScoreSpan = document.querySelector(`.factor-score[data-factor-id="${derivedFactor.id}"]`);
                    //                    if (derivedValueSpan) derivedValueSpan.textContent = derivedFactor.raw_value;
                    if (derivedScoreSpan) {
                        derivedScoreSpan.textContent = derivedFactor.new_score
                    }
                }
                // Show toast notification
                const factorName = document.querySelector(`.factor-label[data-factor-id="${factorId}"]`).textContent;
                const overallScore = data.updated_derived_factors.find(df => df.factor_name === 'overallScore')?.new_score;
                showToast(`${factorName} is now updated with "${selectField.value}". Overall Score is now ${parseFloat(overallScore).toFixed(2)}.`);
            } else {
                console.error('Update failed:', data.error);
                alert('Failed to update value. Please try again.');
            }
        }).catch((error) => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });

        valueSpan.classList.remove('hidden');
        selectField.classList.add('hidden');

        // Change save button back to edit button
        saveButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
        `;
        saveButton.classList.add('edit-btn');
        saveButton.classList.remove('save-btn');
    }
});
function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg transition-opacity duration-500 ease-in-out';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 500);
        }, 5000);
}