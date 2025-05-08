/**
 * Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
 * Author: Coderthemes
 * Component: Dragula component
 */

// Dragula (Draggable Components)
class Dragula {
	initDragula() {
		document.querySelectorAll('[data-plugin="dragula"]').forEach(function (element) {
			var containersIds = element.getAttribute('data-containers');
			var containers = [];

			if (containersIds) {
				containersIds = JSON.parse(containersIds); // Assuming containersIds is a JSON string
				containersIds.forEach(function (id) {
					containers.push(document.getElementById(id));
				});
			} else {
				containers = [element];
			}

			var handleClass = element.getAttribute('data-handleclass');

			if (handleClass) {
				dragula(containers, {
					moves: function (el, container, handle) {
						return handle.classList.contains(handleClass);
					}
				});
			} else {
				dragula(containers);
			}
		});
	}

	init() {
		this.initDragula();
	}
}

document.addEventListener('DOMContentLoaded', function (e) {
	new Dragula().init();
});
