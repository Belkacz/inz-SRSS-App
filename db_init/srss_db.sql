-- phpMyAdmin SQL Dump
-- version 5.2.3-1.fc43
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Lis 12, 2025 at 09:29 PM
-- Wersja serwera: 10.11.13-MariaDB
-- Wersja PHP: 8.4.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Baza danych: `srss_db`
--

-- --------------------------------------------------------

--
-- Struktura tabeli dla tabeli `alert_history`
--

CREATE TABLE `alert_history` (
  `id` int(11) NOT NULL,
  `server_room_id_fk` int(11) DEFAULT NULL,
  `alert_level` int(11) DEFAULT NULL,
  `date` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Struktura tabeli dla tabeli `general_settings`
--

CREATE TABLE `general_settings` (
  `id` int(11) NOT NULL,
  `alert_level` int(11) DEFAULT NULL,
  `alert_delay` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Struktura tabeli dla tabeli `privilages`
--

CREATE TABLE `privilages` (
  `id` int(11) NOT NULL,
  `privalige_name` varchar(512) DEFAULT NULL,
  `privilage_level_fk` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Zrzut danych tabeli `privilages`
--

INSERT INTO `privilages` (`id`, `privalige_name`, `privilage_level_fk`) VALUES
(1, 'admin', 1),
(2, 'observer', 2),
(3, 'guest', 3);

-- --------------------------------------------------------

--
-- Struktura tabeli dla tabeli `server_room`
--

CREATE TABLE `server_room` (
  `id` int(11) NOT NULL,
  `adress` varchar(512) DEFAULT NULL,
  `short_name` varchar(512) DEFAULT NULL,
  `level` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Struktura tabeli dla tabeli `user`
--

CREATE TABLE `user` (
  `id` int(11) NOT NULL,
  `card_number` bigint(20) DEFAULT NULL,
  `first_name` varchar(512) DEFAULT NULL,
  `second_name` varchar(512) DEFAULT NULL,
  `email` varchar(512) DEFAULT NULL,
  `supervisor` varchar(255) DEFAULT NULL,
  `privilage_id_fk` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Zrzut danych tabeli `user`
--

INSERT INTO `user` (`id`, `card_number`, `first_name`, `second_name`, `email`, `supervisor`, `privilage_id_fk`) VALUES
(1, 3473812993, 'user1', 'user1Surname', 'test1@gmail.com', 'admin1', 1),
(2, 3473793399, 'user2', 'user2Surname', 'test2@gmail.com', 'admin1', 1),
(3, 3473758819, 'user3', 'user3Surname', 'test3@gmail.com', 'admin1', 1),
(4, 3473759500, 'user4', 'user4Surname', 'test4@gmail.com', 'admin1', 1);

--
-- Indeksy dla zrzutów tabel
--

--
-- Indeksy dla tabeli `alert_history`
--
ALTER TABLE `alert_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `server_room_id_fk` (`server_room_id_fk`);

--
-- Indeksy dla tabeli `general_settings`
--
ALTER TABLE `general_settings`
  ADD PRIMARY KEY (`id`);

--
-- Indeksy dla tabeli `privilages`
--
ALTER TABLE `privilages`
  ADD PRIMARY KEY (`id`);

--
-- Indeksy dla tabeli `server_room`
--
ALTER TABLE `server_room`
  ADD PRIMARY KEY (`id`);

--
-- Indeksy dla tabeli `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`id`),
  ADD KEY `privilage_id_fk` (`privilage_id_fk`);

--
-- AUTO_INCREMENT dla zrzuconych tabel
--

--
-- AUTO_INCREMENT dla tabeli `alert_history`
--
ALTER TABLE `alert_history`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT dla tabeli `general_settings`
--
ALTER TABLE `general_settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT dla tabeli `privilages`
--
ALTER TABLE `privilages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT dla tabeli `server_room`
--
ALTER TABLE `server_room`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT dla tabeli `user`
--
ALTER TABLE `user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Ograniczenia dla zrzutów tabel
--

--
-- Ograniczenia dla tabeli `alert_history`
--
ALTER TABLE `alert_history`
  ADD CONSTRAINT `alert_history_ibfk_1` FOREIGN KEY (`server_room_id_fk`) REFERENCES `server_room` (`id`);

--
-- Ograniczenia dla tabeli `user`
--
ALTER TABLE `user`
  ADD CONSTRAINT `user_ibfk_1` FOREIGN KEY (`privilage_id_fk`) REFERENCES `privilages` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
