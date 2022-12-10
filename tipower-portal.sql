CREATE TABLE `zaehlerx_day` (
  `time` timestamp NOT NULL,
  `value` double NOT NULL,
  PRIMARY KEY (time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `zaehlerx_15m` (
  `time` timestamp NOT NULL,
  `value` double NOT NULL,
  PRIMARY KEY (time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
