-- Sample incidents in the format the detection pipeline writes.
-- Usage (MySQL): mysql -u root -p violence_system_db < sql/sample_violence_events.sql

INSERT INTO violence_events
(Camera_ID, Timestamp, location, Severity, Confidence, evidence, status)
VALUES
('CAM01', '2026-04-09 14:11:21', 'Entrance Gate', 'High', '94%', '/media/evidence/clip5.gif', 'Active'),
('CAM02', '2026-04-09 15:11:21', 'Parking Area', 'Medium', '85%', '/media/evidence/clip6.gif', 'Under Review'),
('CAM03', '2026-04-09 18:11:21', 'Lobby', 'Low', '70%', '/media/evidence/clip1.mp4', 'Resolved'),
('CAM05', '2026-04-10 18:30:00', 'Main Gate', 'High', '0.94', '/media/evidence/clip2.mp4', 'Active'),
('CAM06', '2026-04-11 19:10:00', 'Parking B', 'Medium', '0.81', '/media/evidence/clip3.mp4', 'Under Review'),
('CAM04', '2026-04-12 09:25:00', 'Lobby', 'Low', '0.66', '/media/evidence/clip4.mp4', 'Resolved');








