$fa=5;$fs=0.01;


difference(){
	union() {
		cube(center = true, size = [3.0000000000, 70.0000000000, 127.6000000000]);
		union() {
			translate(v = [0, -29.5000000000, 0]) {
				translate(v = [14.5000000000, 0, 0]) {
					cube(center = true, size = [26.0000000000, 11.0000000000, 12.0000000000]);
				}
			}
			translate(v = [0, -40.0000000000, 0]) {
				translate(v = [25.5000000000, 0, 0]) {
					cube(center = true, size = [4.0000000000, 10.0000000000, 12.0000000000]);
				}
			}
			translate(v = [0, 31.0000000000, 0]) {
				translate(v = [14.5000000000, 0, 0]) {
					translate(v = [0, 0, 32.2000000000]) {
						cube(center = true, size = [26.0000000000, 8.0000000000, 12.0000000000]);
					}
				}
			}
			translate(v = [0, 40.0000000000, 0]) {
				translate(v = [22.5000000000, 0, 0]) {
					translate(v = [0, 0, 32.2000000000]) {
						cube(center = true, size = [10.0000000000, 10.0000000000, 12.0000000000]);
					}
				}
			}
		}
		translate(v = [0, -20.0000000000, 0]) {
			translate(v = [1.5000000000, 0, 0]) {
				translate(v = [0, 0, -6.0000000000]) {
					polyhedron(faces = [[0, 1, 2, 3], [5, 4, 3, 2], [0, 4, 5, 1], [0, 3, 4], [5, 2, 1]], points = [[0, 0, 0], [0, 0, 12.0000000000], [0, -4.0000000000, 12.0000000000], [0, -4.0000000000, 0], [2.3200000000, -4.0000000000, 0], [2.3200000000, -4.0000000000, 12.0000000000]]);
				}
			}
		}
	}
	/* Holes Below*/
	union(){
		translate(v = [1.5000000000, 0, 0]) {
			translate(v = [0, 1.2850000000, 0]) {
				translate(v = [0, 0, 53.6250000000]) {
					cube(center = true, size = [3.0000000000, 42.5500000000, 2.5500000000]);
				}
			}
		}
		translate(v = [0, -18.7150000000, 0]) {
			translate(v = [1.5000000000, 0, 0]) {
				cube(center = true, size = [3.0000000000, 2.5500000000, 109.8000000000]);
			}
		}
		translate(v = [0, 21.2850000000, 0]) {
			translate(v = [1.5000000000, 0, 0]) {
				translate(v = [0, 0, 34.2500000000]) {
					cube(center = true, size = [3.0000000000, 2.5500000000, 41.3000000000]);
				}
			}
		}
		translate(v = [1.5000000000, 0, 0]) {
			translate(v = [0, -6.2200000000, 0]) {
				translate(v = [0, 0, 14.8750000000]) {
					cube(center = true, size = [3.0000000000, 57.5600000000, 2.5500000000]);
				}
			}
		}
		translate(v = [1.5000000000, 0, 0]) {
			translate(v = [0, 1.2850000000, 0]) {
				translate(v = [0, 0, -53.6250000000]) {
					cube(center = true, size = [3.0000000000, 42.5500000000, 2.5500000000]);
				}
			}
		}
		translate(v = [0, 21.2850000000, 0]) {
			translate(v = [1.5000000000, 0, 0]) {
				translate(v = [0, 0, -34.2500000000]) {
					cube(center = true, size = [3.0000000000, 2.5500000000, 41.3000000000]);
				}
			}
		}
		translate(v = [0, 1.2850000000, 0]) {
			translate(v = [1.5000000000, 0, 0]) {
				translate(v = [0, 0, -14.8750000000]) {
					cube(center = true, size = [3.0000000000, 42.5500000000, 2.5500000000]);
				}
			}
		}
	} /* End Holes */ 
}