<script>
document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const settingsButton = document.getElementById('settingsButton');
    const settingsMenu = document.getElementById('settingsMenu');

    const editButtons = document.querySelectorAll('.edit-btn');
        function activateTab(tabName) {
            tabContents.forEach(content => content.classList.add('hidden'));
            tabs.forEach(tab => tab.classList.remove('active'));

            const activeContent = document.getElementById(tabName);
            const activeTab = document.querySelector(`[data-tab="${tabName}"]`);

            if (activeContent) activeContent.classList.remove('hidden');
            if (activeTab) activeTab.classList.add('active');
        }
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            activateTab(tab.getAttribute('data-tab'));
        });
    });

    // Activate the first tab by default in tabbed view
    if (tabs.length > 0 && '{{ view_type }}' === 'tabbed') {
        activateTab(tabs[0].getAttribute('data-tab'));
    }

    // Toggle settings menu
    settingsButton.addEventListener('click', () => {
        settingsMenu.classList.toggle('hidden');
    });

    // Close settings menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!settingsButton.contains(e.target) && !settingsMenu.contains(e.target)) {
            settingsMenu.classList.add('hidden');
        }
    });
});
</script>