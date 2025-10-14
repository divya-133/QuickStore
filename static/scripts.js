// scripts.js

// Simple client-side search
document.addEventListener("DOMContentLoaded", () => {
  const searchForm = document.querySelector(".search-form");
  const searchInput = searchForm?.querySelector("input[name='q']");
  
  if (searchForm && searchInput) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const query = searchInput.value.toLowerCase();
      const products = document.querySelectorAll(".product");
      
      products.forEach(product => {
        const title = product.querySelector("h3").textContent.toLowerCase();
        if (title.includes(query)) {
          product.style.display = "block";
        } else {
          product.style.display = "none";
        }
      });

      if (query.trim() === "") {
        products.forEach(product => product.style.display = "block");
      }
    });
  }
});
