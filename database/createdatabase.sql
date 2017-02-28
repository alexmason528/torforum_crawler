-- MySQL dump 10.16  Distrib 10.1.19-MariaDB, for CYGWIN (x86_64)
--
-- Host: 127.0.0.1    Database: 127.0.0.1
-- ------------------------------------------------------
-- Server version	5.7.14

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `captcha_question`
--

DROP TABLE IF EXISTS `captcha_question`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `captcha_question` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `forum` bigint(11) NOT NULL,
  `hash` varchar(255) NOT NULL,
  `question` text,
  `answer` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `hash_UNIQUE` (`forum`,`hash`),
  KEY `question_forum_idx` (`forum`),
  CONSTRAINT `question_forum` FOREIGN KEY (`forum`) REFERENCES `forum` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `forum`
--

DROP TABLE IF EXISTS `forum`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `forum` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `spider` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`),
  UNIQUE KEY `spider_UNIQUE` (`spider`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `message`
--

DROP TABLE IF EXISTS `message`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `message` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `external_id` tinytext,
  `thread` bigint(11) NOT NULL,
  `author` bigint(11) DEFAULT NULL,
  `contenttext` longtext,
  `contenthtml` longtext,
  `posted_on` timestamp NULL DEFAULT NULL,
  `modified_on` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `forum` bigint(11) NOT NULL,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `message_forum_extid_unique` (`forum`,`external_id`(255)),
  KEY `message_user_idx` (`author`),
  KEY `message_thread_idx` (`thread`),
  KEY `message_forum_idx` (`forum`),
  KEY `message_scrape_fk_idx` (`scrape`),
  CONSTRAINT `message_forum_fk` FOREIGN KEY (`forum`) REFERENCES `forum` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `message_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `message_thread_fk` FOREIGN KEY (`thread`) REFERENCES `thread` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `message_user_fk` FOREIGN KEY (`author`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPRESSED KEY_BLOCK_SIZE=4;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER message_before_update_audit 
    BEFORE UPDATE ON message
    FOR EACH ROW 
BEGIN
	IF NEW.`contenttext` <> OLD.`contenttext` or NEW.`contenthtml` <> OLD.`contenthtml` or NEW.`posted_on` <> OLD.`posted_on` or NEW.`author` <> OLD.`author`
	THEN  
		INSERT INTO `torforum_crawler`.`message_audit`
			(`message`,`author`,`contenttext`,`contenthtml`,`posted_on`,`modified_on`,`scrape`)
		VALUES
			(OLD.`id`, old.`author`, OLD.`contenttext`, OLD.`contenthtml`, OLD.`posted_on`, OLD.`modified_on`, OLD.`scrape`);
	END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `message_audit`
--

DROP TABLE IF EXISTS `message_audit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `message_audit` (
  `message` bigint(11) NOT NULL,
  `author` bigint(11) DEFAULT NULL,
  `contenttext` longtext,
  `contenthtml` longtext,
  `posted_on` timestamp NULL DEFAULT NULL,
  `modified_on` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`message`),
  KEY `message_audit_scrape_fk_idx` (`scrape`),
  KEY `message_audit_author_fk_idx` (`author`),
  CONSTRAINT `message_audit_author_fk` FOREIGN KEY (`author`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `message_audit_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPRESSED KEY_BLOCK_SIZE=4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `message_propkey`
--

DROP TABLE IF EXISTS `message_propkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `message_propkey` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `message_propkey_name_UNIQUE` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `message_propval`
--

DROP TABLE IF EXISTS `message_propval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `message_propval` (
  `propkey` bigint(11) NOT NULL,
  `message` bigint(11) NOT NULL,
  `data` text,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`propkey`,`message`),
  KEY `message_propval_msg` (`message`),
  KEY `message_propval_msgkey_index` (`propkey`,`message`),
  KEY `message_propval_scrape_index` (`scrape`),
  KEY `message_propval_modifiedon_index` (`modified_on`),
  CONSTRAINT `message_propkey_fk` FOREIGN KEY (`propkey`) REFERENCES `message_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `message_propval_msg_fk` FOREIGN KEY (`message`) REFERENCES `message` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `message_propval_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER message_propval_before_update_audit 
    BEFORE UPDATE ON message_propval
    FOR EACH ROW 
BEGIN
	IF NEW.`data` <> OLD.`data`
	THEN  
		insert into `message_propvalaudit`
			(`modified_on`, `message`, `propkey`, `data`, `scrape`)
		values
			(OLD.`modified_on`, OLD.`message`, OLD.`propkey`, OLD.`data`, OLD.`scrape`);
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `message_propvalaudit`
--

DROP TABLE IF EXISTS `message_propvalaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `message_propvalaudit` (
  `propkey` bigint(11) NOT NULL,
  `message` bigint(11) NOT NULL,
  `data` text,
  `modified_on` timestamp NOT NULL,
  `scrape` bigint(11) DEFAULT NULL,
  KEY `message_propvalaudit_modifiedon_index` (`modified_on`),
  KEY `message_propvalaudit_scrape_index` (`scrape`),
  KEY `message_propvalaudit_user_idx` (`message`),
  KEY `message_propvalaudit_propkey_idx` (`propkey`),
  KEY `message_propvalaudit_messagekey_index` (`message`,`propkey`),
  CONSTRAINT `message_prophistory_message` FOREIGN KEY (`message`) REFERENCES `message` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `message_prophistory_propkey` FOREIGN KEY (`propkey`) REFERENCES `message_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `message_prophistory_scrape` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `overview_by_scrape`
--

DROP TABLE IF EXISTS `overview_by_scrape`;
/*!50001 DROP VIEW IF EXISTS `overview_by_scrape`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE TABLE `overview_by_scrape` (
  `ScrapeId` tinyint NOT NULL,
  `ScrapeStart` tinyint NOT NULL,
  `ScrapeDuration` tinyint NOT NULL,
  `ExitReason` tinyint NOT NULL,
  `Thread` tinyint NOT NULL,
  `Message` tinyint NOT NULL,
  `MessagePropVal` tinyint NOT NULL,
  `User` tinyint NOT NULL,
  `UserPropVal` tinyint NOT NULL
) ENGINE=MyISAM */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `scrape`
--

DROP TABLE IF EXISTS `scrape`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `scrape` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `start` timestamp NULL DEFAULT NULL,
  `end` timestamp NULL DEFAULT NULL,
  `reason` text,
  `forum` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scrape_forum_fk_idx` (`forum`),
  CONSTRAINT `scrape_forum_fk` FOREIGN KEY (`forum`) REFERENCES `forum` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `scrapestat`
--

DROP TABLE IF EXISTS `scrapestat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `scrapestat` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `scrape` bigint(11) NOT NULL,
  `logtime` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `request_sent` bigint(20) DEFAULT NULL,
  `request_bytes` bigint(20) DEFAULT NULL,
  `response_received` bigint(20) DEFAULT NULL,
  `response_bytes` bigint(20) DEFAULT NULL,
  `item_scraped` bigint(20) DEFAULT NULL,
  `thread` bigint(20) DEFAULT NULL,
  `message` bigint(20) DEFAULT NULL,
  `message_propval` bigint(20) DEFAULT NULL,
  `user` bigint(20) DEFAULT NULL,
  `user_propval` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scrapestat_scrape_fk_idx` (`scrape`),
  KEY `scrapestat_scrapetime_idx` (`scrape`,`logtime`),
  CONSTRAINT `scrapestat_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `thread`
--

DROP TABLE IF EXISTS `thread`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `thread` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `external_id` text,
  `forum` bigint(11) NOT NULL,
  `title` text NOT NULL,
  `author` bigint(11) DEFAULT NULL,
  `relativeurl` text,
  `fullurl` text,
  `last_update` timestamp NULL DEFAULT NULL,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_forum_externalid` (`forum`,`external_id`(255)) USING BTREE,
  KEY `thread_forum_idx` (`forum`),
  KEY `thread_author_idx` (`author`),
  KEY `thread_scrape_idx` (`scrape`),
  CONSTRAINT `thread_author_fk` FOREIGN KEY (`author`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `thread_forum_fk` FOREIGN KEY (`forum`) REFERENCES `forum` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `thread_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `forum` bigint(11) NOT NULL,
  `username` varchar(255) DEFAULT NULL,
  `relativeurl` text,
  `fullurl` text,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `forum_username` (`forum`,`username`),
  KEY `author_forum_idx` (`forum`),
  KEY `user_scrape_fk_idx` (`scrape`),
  CONSTRAINT `user_forum_fk` FOREIGN KEY (`forum`) REFERENCES `forum` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_propkey`
--

DROP TABLE IF EXISTS `user_propkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_propkey` (
  `id` bigint(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_propval`
--

DROP TABLE IF EXISTS `user_propval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_propval` (
  `propkey` bigint(11) NOT NULL,
  `user` bigint(11) NOT NULL,
  `data` text,
  `modified_on` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scrape` bigint(11) DEFAULT NULL,
  PRIMARY KEY (`propkey`,`user`),
  KEY `user_propval_user_idx` (`user`),
  KEY `user_propval_userkey_index` (`user`,`propkey`),
  KEY `user_propvap_modifiedon_index` (`modified_on`),
  KEY `user_propval_scrape_fk_idx` (`scrape`),
  CONSTRAINT `user_propkey_key_fk` FOREIGN KEY (`propkey`) REFERENCES `user_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_propval_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `user_propval_user_fk` FOREIGN KEY (`user`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER user_propval_before_update_audit 
    BEFORE UPDATE ON user_propval
    FOR EACH ROW 
BEGIN
	IF NEW.`data` <> OLD.`data`
	THEN  
		insert into `user_propvalaudit`
			(`modified_on`, `user`, `propkey`, `data`, `scrape`)
		values
			(OLD.`modified_on`, OLD.`user`, OLD.`propkey`, OLD.`data`, OLD.`scrape`);
	END IF;
 END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `user_propvalaudit`
--

DROP TABLE IF EXISTS `user_propvalaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_propvalaudit` (
  `propkey` bigint(11) NOT NULL,
  `user` bigint(11) NOT NULL,
  `data` text,
  `modified_on` timestamp NOT NULL,
  `scrape` bigint(11) DEFAULT NULL,
  KEY `user_propvalaudit_user_idx` (`user`),
  KEY `user_propvalaudit_propkey_idx` (`propkey`),
  KEY `user_propvalaudit_userkey_index` (`user`,`propkey`),
  KEY `user_provalaudit_scrape_fk_idx` (`scrape`),
  KEY `user_propvalaudit_modifiedon_index` (`modified_on`),
  CONSTRAINT `user_propvalaudit_propkey_fk` FOREIGN KEY (`propkey`) REFERENCES `user_propkey` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_propvalaudit_user_fk` FOREIGN KEY (`user`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_provalaudit_scrape_fk` FOREIGN KEY (`scrape`) REFERENCES `scrape` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Final view structure for view `overview_by_scrape`
--

/*!50001 DROP TABLE IF EXISTS `overview_by_scrape`*/;
/*!50001 DROP VIEW IF EXISTS `overview_by_scrape`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 */
/*!50001 VIEW `overview_by_scrape` AS select ifnull(`s`.`ScrapeID`,0) AS `ScrapeId`,ifnull(`s`.`ScrapeStart`,0) AS `ScrapeStart`,`s`.`ScrapeDuration` AS `ScrapeDuration`,`s`.`ExitReason` AS `ExitReason`,ifnull(`t`.`Thread`,0) AS `Thread`,ifnull(`m`.`Message`,0) AS `Message`,ifnull(`mv`.`MessagePropVal`,0) AS `MessagePropVal`,ifnull(`u`.`User`,0) AS `User`,ifnull(`uv`.`UserPropVal`,0) AS `UserPropVal` from (((((((select `torforum_crawler`.`scrape`.`id` AS `ScrapeID`,`torforum_crawler`.`scrape`.`start` AS `ScrapeStart`,timediff(`torforum_crawler`.`scrape`.`end`,`torforum_crawler`.`scrape`.`start`) AS `ScrapeDuration`,`torforum_crawler`.`scrape`.`reason` AS `ExitReason` from `torforum_crawler`.`scrape`)) `s` left join (select `torforum_crawler`.`user`.`scrape` AS `scrape`,count(1) AS `User` from `torforum_crawler`.`user` group by `torforum_crawler`.`user`.`scrape`) `u` on((`u`.`scrape` = `s`.`ScrapeID`))) left join (select `torforum_crawler`.`message`.`scrape` AS `scrape`,count(1) AS `Message` from `torforum_crawler`.`message` group by `torforum_crawler`.`message`.`scrape`) `m` on((`m`.`scrape` = `s`.`ScrapeID`))) left join (select `sumedmv`.`scrape` AS `scrape`,sum(`sumedmv`.`MessagePropVal`) AS `MessagePropVal` from ((select `torforum_crawler`.`message_propval`.`scrape` AS `scrape`,ifnull(count(1),0) AS `MessagePropVal` from `torforum_crawler`.`message_propval` group by `torforum_crawler`.`message_propval`.`scrape`) union all (select `torforum_crawler`.`message_propvalaudit`.`scrape` AS `scrape`,ifnull(count(1),0) AS `MessagePropVal` from `torforum_crawler`.`message_propvalaudit` group by `torforum_crawler`.`message_propvalaudit`.`scrape`)) `sumedmv` group by `sumedmv`.`scrape`) `mv` on((`mv`.`scrape` = `s`.`ScrapeID`))) left join (select `torforum_crawler`.`thread`.`scrape` AS `scrape`,count(1) AS `Thread` from `torforum_crawler`.`thread` group by `torforum_crawler`.`thread`.`scrape`) `t` on((`t`.`scrape` = `s`.`ScrapeID`))) left join (select `sumeduv`.`scrape` AS `scrape`,sum(`sumeduv`.`UserPropVal`) AS `UserPropVal` from ((select `torforum_crawler`.`user_propval`.`scrape` AS `scrape`,ifnull(count(1),0) AS `UserPropVal` from `torforum_crawler`.`user_propval` group by `torforum_crawler`.`user_propval`.`scrape`) union all (select `torforum_crawler`.`user_propvalaudit`.`scrape` AS `scrape`,ifnull(count(1),0) AS `UserPropVal` from `torforum_crawler`.`user_propvalaudit` group by `torforum_crawler`.`user_propvalaudit`.`scrape`)) `sumeduv` group by `sumeduv`.`scrape`) `uv` on((`uv`.`scrape` = `s`.`ScrapeID`))) order by ifnull(`s`.`ScrapeID`,0) desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2017-02-28  0:31:36
