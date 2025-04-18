CREATE TABLE IF NOT EXISTS `groups` (
	`group_id` integer primary key NOT NULL UNIQUE,
	`group_name` TEXT NOT NULL UNIQUE,
	`group_profile` TEXT NOT NULL,
	`picture_path` TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS `members` (
	`member_id` integer primary key NOT NULL UNIQUE,
	`group_id` INTEGER NOT NULL,
	`member_name` TEXT NOT NULL,
	`picture_path` TEXT NOT NULL,
FOREIGN KEY(`group_id`) REFERENCES `groups`(`group_id`)
);
CREATE TABLE IF NOT EXISTS `songs` (
	`song_id` integer primary key NOT NULL UNIQUE,
	`song_title` TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS `performances` (
	`performance_id` integer primary key NOT NULL UNIQUE,
	`group_id` INTEGER NOT NULL,
	`performance_date` TEXT NOT NULL,
	`show_type` TEXT NOT NULL,
	`resolution` TEXT NOT NULL,
	`file_path` TEXT NOT NULL,
	`score` INTEGER NOT NULL,
	`notes` TEXT NOT NULL,
FOREIGN KEY(`group_id`) REFERENCES `groups`(`group_id`)
);
CREATE TABLE IF NOT EXISTS `performance_songs` (
	`performance_id` INTEGER NOT NULL,
	`song_id` INTEGER NOT NULL,
FOREIGN KEY(`performance_id`) REFERENCES `performances`(`performance_id`),
FOREIGN KEY(`song_id`) REFERENCES `songs`(`song_id`)
);
CREATE TABLE IF NOT EXISTS `music_videos` (
	`mv_id` integer primary key NOT NULL UNIQUE,
	`group_id` INTEGER NOT NULL,
	`song_id` INTEGER NOT NULL,
	`release_date` TEXT NOT NULL,
	`file_path` TEXT NOT NULL,
	`score` INTEGER NOT NULL,
	`title` TEXT NOT NULL,
FOREIGN KEY(`group_id`) REFERENCES `groups`(`group_id`),
FOREIGN KEY(`song_id`) REFERENCES `songs`(`song_id`)
);
CREATE TABLE IF NOT EXISTS `fancams` (
	`fancam_id` integer primary key NOT NULL UNIQUE,
	`group_id` INTEGER NOT NULL,
	`member_id` INTEGER NOT NULL,
	`performance_date` TEXT NOT NULL,
	`song_id` INTEGER NOT NULL,
	`file_path` TEXT NOT NULL,
	`score` INTEGER NOT NULL,
	`focus_details` TEXT NOT NULL,
FOREIGN KEY(`group_id`) REFERENCES `groups`(`group_id`),
FOREIGN KEY(`member_id`) REFERENCES `members`(`member_id`),
FOREIGN KEY(`song_id`) REFERENCES `songs`(`song_id`)
);