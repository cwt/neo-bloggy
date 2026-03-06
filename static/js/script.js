/* 
    Back to Top button
*/
//Get the button
let mybutton = document.getElementById("btn-back-to-top");

// When the user scrolls down 20px from the top of the document, show the button
if (mybutton) {
  window.onscroll = function () {
    scrollFunction();
  };

  function scrollFunction() {
    if (
      document.body.scrollTop > 20 ||
      document.documentElement.scrollTop > 20
    ) {
      mybutton.style.display = "block";
    } else {
      mybutton.style.display = "none";
    }
  }
  // When the user clicks on the button, scroll to the top of the document
  mybutton.addEventListener("click", backToTop);

  function backToTop() {
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;
  }
}

/**
 * Modern Responsive Table Wrapper
 * Automatically wraps tables in post content and comments with a responsive container
 */
document.addEventListener('DOMContentLoaded', function() {
    function wrapTables() {
        const containers = document.querySelectorAll('.post-content, .commentText');
        containers.forEach(container => {
            const tables = container.querySelectorAll('table');
            tables.forEach(table => {
                // Skip if already wrapped or if it's a specific UI table
                if (table.parentElement.classList.contains('table-responsive-wrapper') || 
                    table.classList.contains('profile-table')) {
                    return;
                }
                
                // Create wrapper
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive-wrapper';
                
                // Insert wrapper before table and move table inside
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            });
        });
    }

    // Run once on load
    wrapTables();
    
    // Also run when EasyMDE preview is toggled (it might add tables dynamically)
    // We can listen for clicks on preview buttons or use MutationObserver
    document.addEventListener('click', function(e) {
        if (e.target.closest('.preview')) {
            // Wait a bit for EasyMDE to render the preview
            setTimeout(wrapTables, 50);
        }
    });
});
