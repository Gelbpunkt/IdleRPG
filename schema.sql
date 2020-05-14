-- The IdleRPG Discord Bot
-- Copyright (C) 2018-2020 Diniboy and Gelbpunkt

-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU Affero General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU Affero General Public License for more details.
-- You should have received a copy of the GNU Affero General Public License
-- along with this program.  If not, see <https://www.gnu.org/licenses/>.


--
-- PostgreSQL database dump
--

-- Dumped from database version 12.2
-- Dumped by pg_dump version 12.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: rgba; Type: TYPE; Schema: public; Owner: jens
--

CREATE TYPE public.rgba AS (
	red integer,
	green integer,
	blue integer,
	alpha real
);


ALTER TYPE public.rgba OWNER TO jens;

--
-- Name: insert_alliance_default(); Type: FUNCTION; Schema: public; Owner: jens
--

CREATE FUNCTION public.insert_alliance_default() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
if NEW.alliance is null then
NEW.alliance := NEW.id;
end if;
return new;
end;
$$;


ALTER FUNCTION public.insert_alliance_default() OWNER TO jens;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: allitems; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.allitems (
    id bigint NOT NULL,
    owner bigint,
    name character varying(200) NOT NULL,
    value integer NOT NULL,
    type character varying(10) NOT NULL,
    damage numeric(5,2) NOT NULL,
    armor numeric(5,2) NOT NULL,
    signature character varying(50) DEFAULT NULL::character varying,
    original_type character varying(10) DEFAULT NULL::character varying,
    original_name character varying(200) DEFAULT NULL::character varying,
    hand character varying(10) NOT NULL
);


ALTER TABLE public.allitems OWNER TO jens;

--
-- Name: allitems_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.allitems_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.allitems_id_seq OWNER TO jens;

--
-- Name: allitems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.allitems_id_seq OWNED BY public.allitems.id;


--
-- Name: chess_matches; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.chess_matches (
    id integer NOT NULL,
    player1 bigint,
    player2 bigint,
    result character varying(7) NOT NULL,
    pgn text NOT NULL,
    winner bigint
);


ALTER TABLE public.chess_matches OWNER TO jens;

--
-- Name: chess_matches_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.chess_matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chess_matches_id_seq OWNER TO jens;

--
-- Name: chess_matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.chess_matches_id_seq OWNED BY public.chess_matches.id;


--
-- Name: chess_players; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.chess_players (
    "user" bigint NOT NULL,
    elo bigint DEFAULT 1000 NOT NULL
);


ALTER TABLE public.chess_players OWNER TO jens;

--
-- Name: children; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.children (
    mother bigint,
    father bigint,
    name character varying(20),
    age bigint,
    gender character varying(10)
);


ALTER TABLE public.children OWNER TO jens;

--
-- Name: city; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.city (
    name character varying(25) NOT NULL,
    owner bigint NOT NULL,
    thief_building integer DEFAULT 0,
    raid_building integer DEFAULT 0,
    trade_building integer DEFAULT 0,
    adventure_building integer DEFAULT 0
);


ALTER TABLE public.city OWNER TO jens;

--
-- Name: coupon; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.coupon (
    "from" bigint NOT NULL,
    "to" bigint,
    created_at timestamp with time zone DEFAULT now(),
    code character varying(10) NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.coupon OWNER TO jens;

--
-- Name: coupon_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.coupon_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.coupon_id_seq OWNER TO jens;

--
-- Name: coupon_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.coupon_id_seq OWNED BY public.coupon.id;


--
-- Name: defenses; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.defenses (
    city character varying(25) NOT NULL,
    name character varying(25) NOT NULL,
    hp integer NOT NULL,
    defense integer NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.defenses OWNER TO jens;

--
-- Name: defenses_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.defenses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.defenses_id_seq OWNER TO jens;

--
-- Name: defenses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.defenses_id_seq OWNED BY public.defenses.id;


--
-- Name: guild; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.guild (
    id integer NOT NULL,
    name character varying(20) NOT NULL,
    memberlimit bigint NOT NULL,
    leader bigint,
    icon character varying(60),
    money bigint DEFAULT 0,
    wins bigint DEFAULT 0,
    banklimit bigint DEFAULT 250000,
    badges text[],
    badge character varying(100) DEFAULT NULL::character varying,
    description character varying(200) DEFAULT 'No Description set yet'::character varying NOT NULL,
    channel bigint,
    upgrade bigint DEFAULT 1 NOT NULL,
    alliance bigint
);


ALTER TABLE public.guild OWNER TO jens;

--
-- Name: guild_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.guild_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.guild_id_seq OWNER TO jens;

--
-- Name: guild_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.guild_id_seq OWNED BY public.guild.id;


--
-- Name: helpme; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.helpme (
    id bigint NOT NULL
);


ALTER TABLE public.helpme OWNER TO jens;

--
-- Name: inventory; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.inventory (
    id bigint NOT NULL,
    item bigint,
    equipped boolean NOT NULL
);


ALTER TABLE public.inventory OWNER TO jens;

--
-- Name: inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.inventory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.inventory_id_seq OWNER TO jens;

--
-- Name: inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.inventory_id_seq OWNED BY public.inventory.id;


--
-- Name: loot; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.loot (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    value bigint NOT NULL,
    "user" bigint NOT NULL
);


ALTER TABLE public.loot OWNER TO jens;

--
-- Name: loot_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.loot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.loot_id_seq OWNER TO jens;

--
-- Name: loot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.loot_id_seq OWNED BY public.loot.id;


--
-- Name: market; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.market (
    id bigint NOT NULL,
    item bigint,
    price integer NOT NULL,
    published timestamp with time zone DEFAULT now()
);


ALTER TABLE public.market OWNER TO jens;

--
-- Name: market_history; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.market_history (
    id integer NOT NULL,
    item bigint NOT NULL,
    name character varying(200) NOT NULL,
    value integer NOT NULL,
    type character varying(10) NOT NULL,
    damage numeric(5,2) NOT NULL,
    armor numeric(5,2) NOT NULL,
    signature character varying(50) DEFAULT NULL::character varying,
    price bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    offer bigint NOT NULL
);


ALTER TABLE public.market_history OWNER TO jens;

--
-- Name: market_history_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.market_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.market_history_id_seq OWNER TO jens;

--
-- Name: market_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.market_history_id_seq OWNED BY public.market_history.id;


--
-- Name: market_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.market_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.market_id_seq OWNER TO jens;

--
-- Name: market_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.market_id_seq OWNED BY public.market.id;


--
-- Name: pets; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.pets (
    "user" bigint NOT NULL,
    name character varying(20) DEFAULT 'Kevin'::character varying NOT NULL,
    image character varying(60) DEFAULT 'https://i.imgur.com/IHhXjXg.jpg'::character varying NOT NULL,
    food bigint DEFAULT 100 NOT NULL,
    drink bigint DEFAULT 100 NOT NULL,
    love bigint DEFAULT 100 NOT NULL,
    joy bigint DEFAULT 100 NOT NULL,
    last_update timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


ALTER TABLE public.pets OWNER TO jens;

--
-- Name: profile; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.profile (
    "user" bigint NOT NULL,
    name character varying(20),
    money bigint,
    xp integer,
    pvpwins bigint DEFAULT 0 NOT NULL,
    money_booster bigint DEFAULT 0,
    time_booster bigint DEFAULT 0,
    luck_booster bigint DEFAULT 0,
    marriage bigint DEFAULT 0,
    background character varying(60) DEFAULT 0,
    guild bigint DEFAULT 0,
    class character varying(50)[] DEFAULT '{"No Class","No Class"}'::character varying[],
    deaths bigint DEFAULT 0,
    completed bigint DEFAULT 0,
    lovescore bigint DEFAULT 0 NOT NULL,
    guildrank character varying(20) DEFAULT 'Member'::character varying,
    backgrounds text[],
    puzzles bigint DEFAULT 0,
    atkmultiply numeric DEFAULT 1.0,
    defmultiply numeric DEFAULT 1.0,
    crates_common bigint DEFAULT 0,
    crates_uncommon bigint DEFAULT 0,
    crates_rare bigint DEFAULT 0,
    crates_magic bigint DEFAULT 0,
    crates_legendary bigint DEFAULT 0,
    luck numeric DEFAULT 1.0,
    god character varying(50) DEFAULT NULL::character varying,
    favor bigint DEFAULT 0,
    race character varying(30) DEFAULT 'Human'::character varying,
    cv bigint DEFAULT '-1'::integer,
    reset_points bigint DEFAULT 2 NOT NULL,
    chocolates integer DEFAULT 0,
    trickortreat bigint DEFAULT 0,
    eastereggs bigint DEFAULT 0,
    colour public.rgba DEFAULT '(0,0,0,1)'::public.rgba
);


ALTER TABLE public.profile OWNER TO jens;

--
-- Name: server; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.server (
    id bigint,
    prefix character varying(10),
    unknown boolean
);


ALTER TABLE public.server OWNER TO jens;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    "from" bigint NOT NULL,
    "to" bigint NOT NULL,
    subject character varying(50) NOT NULL,
    info character varying(582) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL
);


ALTER TABLE public.transactions OWNER TO jens;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: jens
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transactions_id_seq OWNER TO jens;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jens
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: user_settings; Type: TABLE; Schema: public; Owner: jens
--

CREATE TABLE public.user_settings (
    "user" bigint NOT NULL,
    locale character varying(20) NOT NULL
);


ALTER TABLE public.user_settings OWNER TO jens;

--
-- Name: allitems id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.allitems ALTER COLUMN id SET DEFAULT nextval('public.allitems_id_seq'::regclass);


--
-- Name: chess_matches id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.chess_matches ALTER COLUMN id SET DEFAULT nextval('public.chess_matches_id_seq'::regclass);


--
-- Name: coupon id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.coupon ALTER COLUMN id SET DEFAULT nextval('public.coupon_id_seq'::regclass);


--
-- Name: defenses id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.defenses ALTER COLUMN id SET DEFAULT nextval('public.defenses_id_seq'::regclass);


--
-- Name: guild id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.guild ALTER COLUMN id SET DEFAULT nextval('public.guild_id_seq'::regclass);


--
-- Name: inventory id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.inventory ALTER COLUMN id SET DEFAULT nextval('public.inventory_id_seq'::regclass);


--
-- Name: loot id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.loot ALTER COLUMN id SET DEFAULT nextval('public.loot_id_seq'::regclass);


--
-- Name: market id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.market ALTER COLUMN id SET DEFAULT nextval('public.market_id_seq'::regclass);


--
-- Name: market_history id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.market_history ALTER COLUMN id SET DEFAULT nextval('public.market_history_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: allitems allitems_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.allitems
    ADD CONSTRAINT allitems_pkey PRIMARY KEY (id);


--
-- Name: chess_matches chess_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.chess_matches
    ADD CONSTRAINT chess_matches_pkey PRIMARY KEY (id);


--
-- Name: chess_players chess_players_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.chess_players
    ADD CONSTRAINT chess_players_pkey PRIMARY KEY ("user");


--
-- Name: city city_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.city
    ADD CONSTRAINT city_pkey PRIMARY KEY (name);


--
-- Name: coupon coupon_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.coupon
    ADD CONSTRAINT coupon_pkey PRIMARY KEY (code);


--
-- Name: defenses defenses_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.defenses
    ADD CONSTRAINT defenses_pkey PRIMARY KEY (id);


--
-- Name: guild guild_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.guild
    ADD CONSTRAINT guild_pkey PRIMARY KEY (id);


--
-- Name: helpme helpme_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.helpme
    ADD CONSTRAINT helpme_pkey PRIMARY KEY (id);


--
-- Name: inventory inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (id);


--
-- Name: loot loot_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.loot
    ADD CONSTRAINT loot_pkey PRIMARY KEY (id);


--
-- Name: market_history market_history_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.market_history
    ADD CONSTRAINT market_history_pkey PRIMARY KEY (id);


--
-- Name: market market_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.market
    ADD CONSTRAINT market_pkey PRIMARY KEY (id);


--
-- Name: pets pets_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.pets
    ADD CONSTRAINT pets_pkey PRIMARY KEY ("user");


--
-- Name: profile profile_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY ("user");


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: user_settings user_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_pkey PRIMARY KEY ("user");


--
-- Name: guild insert_alliance_default; Type: TRIGGER; Schema: public; Owner: jens
--

CREATE TRIGGER insert_alliance_default BEFORE INSERT ON public.guild FOR EACH ROW EXECUTE FUNCTION public.insert_alliance_default();


--
-- Name: allitems allitems_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.allitems
    ADD CONSTRAINT allitems_owner_fkey FOREIGN KEY (owner) REFERENCES public.profile("user") ON DELETE CASCADE;


--
-- Name: chess_matches chess_matches_player1_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.chess_matches
    ADD CONSTRAINT chess_matches_player1_fkey FOREIGN KEY (player1) REFERENCES public.chess_players("user");


--
-- Name: chess_matches chess_matches_player2_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.chess_matches
    ADD CONSTRAINT chess_matches_player2_fkey FOREIGN KEY (player2) REFERENCES public.chess_players("user");


--
-- Name: chess_matches chess_matches_winner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.chess_matches
    ADD CONSTRAINT chess_matches_winner_fkey FOREIGN KEY (winner) REFERENCES public.chess_players("user");


--
-- Name: city city_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.city
    ADD CONSTRAINT city_owner_fkey FOREIGN KEY (owner) REFERENCES public.guild(id);


--
-- Name: defenses defenses_city_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.defenses
    ADD CONSTRAINT defenses_city_fkey FOREIGN KEY (city) REFERENCES public.city(name);


--
-- Name: guild guild_alliance_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.guild
    ADD CONSTRAINT guild_alliance_fkey FOREIGN KEY (alliance) REFERENCES public.guild(id);


--
-- Name: guild guild_leader_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.guild
    ADD CONSTRAINT guild_leader_fkey FOREIGN KEY (leader) REFERENCES public.profile("user");


--
-- Name: inventory inventory_item_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT inventory_item_fkey FOREIGN KEY (item) REFERENCES public.allitems(id) ON DELETE CASCADE;


--
-- Name: loot loot_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.loot
    ADD CONSTRAINT loot_user_fkey FOREIGN KEY ("user") REFERENCES public.profile("user") ON DELETE CASCADE;


--
-- Name: market market_item_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.market
    ADD CONSTRAINT market_item_fkey FOREIGN KEY (item) REFERENCES public.allitems(id) ON DELETE CASCADE;


--
-- Name: pets pets_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.pets
    ADD CONSTRAINT pets_user_fkey FOREIGN KEY ("user") REFERENCES public.profile("user") ON DELETE CASCADE;


--
-- Name: user_settings user_settings_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jens
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_user_fkey FOREIGN KEY ("user") REFERENCES public.profile("user") ON DELETE CASCADE;


--
-- Name: TABLE allitems; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.allitems TO prest;


--
-- Name: TABLE children; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.children TO prest;


--
-- Name: TABLE guild; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.guild TO prest;


--
-- Name: TABLE helpme; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.helpme TO prest;


--
-- Name: TABLE inventory; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.inventory TO prest;


--
-- Name: TABLE loot; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.loot TO prest;


--
-- Name: TABLE market; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.market TO prest;


--
-- Name: TABLE pets; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.pets TO prest;


--
-- Name: TABLE profile; Type: ACL; Schema: public; Owner: jens
--

GRANT ALL ON TABLE public.profile TO votehandler;
GRANT SELECT ON TABLE public.profile TO prest;


--
-- Name: TABLE server; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.server TO prest;


--
-- Name: TABLE transactions; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.transactions TO prest;


--
-- Name: TABLE user_settings; Type: ACL; Schema: public; Owner: jens
--

GRANT SELECT ON TABLE public.user_settings TO prest;


--
-- PostgreSQL database dump complete
--
