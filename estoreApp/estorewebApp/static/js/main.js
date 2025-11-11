document.addEventListener('DOMContentLoaded', () => {
  // ====== NAVIGATION TOGGLE ======
  const menuBtn = document.getElementById('menuBtn');
  const nav = document.getElementById('nav');

  if (menuBtn && nav) {
    // Function to toggle the navigation display
    const toggleNav = () => {
      // Use class-based toggle for better CSS control
      nav.classList.toggle('active');
      // For legacy JS using direct style modification
      if (nav.style.display === 'flex') {
        nav.style.display = '';
      } else {
        // Set display to flex for mobile view
        nav.style.display = 'flex';
        nav.style.flexDirection = 'column'; // Ensure stacked links
      }
    };
    
    // Initial setup for the button click
    menuBtn.addEventListener('click', toggleNav);

    // Close menu when a link is clicked (for small screens)
    const navLinks = nav.querySelectorAll('a');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
          nav.style.display = '';
          nav.classList.remove('active');
        }
      });
    });

    // Adjust menu automatically on resize
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768) {
        nav.style.display = ''; // reset for large screens (CSS handles the display: flex)
        nav.classList.remove('active');
      }
    });
  }

  // ====== SCROLL REVEAL ANIMATION (Used on .reveal class) ======
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 } // Element reveals when 20% visible
  );

  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  // ====== CONTACT FORM HANDLER ======
  const form = document.getElementById('contactForm');
  const formMsg = document.getElementById('formMsg');

  if (form && formMsg) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      formMsg.textContent = '✅ Thank you! We have received your message and will respond shortly.';
      formMsg.style.color = '#00b894'; // Success green
      form.reset();
    });
  }
});