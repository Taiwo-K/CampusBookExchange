-- ============================================================
--  CampusBookExchange — database schema
--  PostgreSQL 13+
--
--  Run once against an empty database:
--      psql "$DATABASE_URL" -f db/schema.sql
--
--  Traces to Section 6 of the design document. Every table here
--  appears in at least one sequence diagram.
--
--  Note on IDs: we use BIGSERIAL rather than UUIDs because they
--  are easier to read while debugging. Sequential IDs are safe
--  here only because every endpoint checks ownership on the
--  server (see FR-7). 
-- ============================================================

DROP TABLE IF EXISTS notifications       CASCADE;
DROP TABLE IF EXISTS watchlists          CASCADE;
DROP TABLE IF EXISTS messages            CASCADE;
DROP TABLE IF EXISTS conversations       CASCADE;
DROP TABLE IF EXISTS listing_photos      CASCADE;
DROP TABLE IF EXISTS listings            CASCADE;
DROP TABLE IF EXISTS user_courses        CASCADE;
DROP TABLE IF EXISTS course_materials    CASCADE;
DROP TABLE IF EXISTS materials           CASCADE;
DROP TABLE IF EXISTS courses             CASCADE;
DROP TABLE IF EXISTS sessions            CASCADE;
DROP TABLE IF EXISTS verification_tokens CASCADE;
DROP TABLE IF EXISTS users               CASCADE;
DROP TABLE IF EXISTS meetup_locations    CASCADE;


-- ------------------------------------------------------------
-- users                                            FR-1, FR-3
-- ------------------------------------------------------------
CREATE TABLE users (
    id             BIGSERIAL     PRIMARY KEY,
    first_name     VARCHAR(100)  NOT NULL,
    last_name      VARCHAR(100)  NOT NULL,
    email          VARCHAR(255)  NOT NULL UNIQUE,
    password_hash  VARCHAR(255)  NOT NULL,
    verified       BOOLEAN       NOT NULL DEFAULT FALSE,
    role           VARCHAR(20)   NOT NULL DEFAULT 'student',
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT users_role_valid  CHECK (role IN ('student', 'admin')),
    -- Defence in depth. The server checks this too (FR-1); this
    -- stops a bad row reaching the table by any other route.
    CONSTRAINT users_email_is_unt CHECK (email LIKE '%unt.edu')
);


-- ------------------------------------------------------------
-- verification_tokens                                    FR-2
--   Token is stored hashed, so reading the table does not let
--   anyone verify another student's account.
-- ------------------------------------------------------------
CREATE TABLE verification_tokens (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ  NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_verification_token_hash ON verification_tokens (token_hash);
CREATE INDEX idx_verification_user       ON verification_tokens (user_id);


-- ------------------------------------------------------------
-- sessions                                               FR-3
-- ------------------------------------------------------------
CREATE TABLE sessions (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token        VARCHAR(255) NOT NULL UNIQUE,
    last_active  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ  NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_token ON sessions (token);
CREATE INDEX idx_sessions_user  ON sessions (user_id);


-- ------------------------------------------------------------
-- courses                                        FR-14, FR-15
-- ------------------------------------------------------------
CREATE TABLE courses (
    id             BIGSERIAL    PRIMARY KEY,
    course_number  VARCHAR(20)  NOT NULL UNIQUE,
    title          VARCHAR(200) NOT NULL,
    department     VARCHAR(100)
);

CREATE INDEX idx_courses_number ON courses (course_number);


-- ------------------------------------------------------------
-- materials                                      FR-15, FR-16
--   transferable = FALSE marks access codes and other items
--   that cannot be resold. FR-17 prices these at retail in both
--   totals and flags the row.
-- ------------------------------------------------------------
CREATE TABLE materials (
    id            BIGSERIAL    PRIMARY KEY,
    title         VARCHAR(300) NOT NULL,
    author        VARCHAR(200),
    edition       VARCHAR(50),
    isbn          VARCHAR(20)  UNIQUE,
    retail_price  NUMERIC(8,2),
    transferable  BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_materials_isbn ON materials (isbn);


-- ------------------------------------------------------------
-- course_materials                                       FR-15
--   A course with no rows here is the "unknown" case: it is
--   excluded from the totals rather than counted as zero.
-- ------------------------------------------------------------
CREATE TABLE course_materials (
    course_id    BIGINT  NOT NULL REFERENCES courses(id)   ON DELETE CASCADE,
    material_id  BIGINT  NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    required     BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (course_id, material_id)
);


-- ------------------------------------------------------------
-- user_courses                                           FR-14
-- ------------------------------------------------------------
CREATE TABLE user_courses (
    id         BIGSERIAL   PRIMARY KEY,
    user_id    BIGINT      NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id  BIGINT      NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    term       VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT user_courses_unique UNIQUE (user_id, course_id, term)
);

CREATE INDEX idx_user_courses_user ON user_courses (user_id, term);


-- ------------------------------------------------------------
-- listings                                   FR-4, FR-6, FR-7
--   The price_matches_type constraint enforces FR-6 in the
--   database: a sale must carry a price, a trade or giveaway
--   must not.
-- ------------------------------------------------------------
CREATE TABLE listings (
    id            BIGSERIAL    PRIMARY KEY,
    seller_id     BIGINT       NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    material_id   BIGINT       REFERENCES materials(id)          ON DELETE SET NULL,
    course_id     BIGINT       REFERENCES courses(id)            ON DELETE SET NULL,
    title         VARCHAR(300) NOT NULL,
    isbn          VARCHAR(20),
    price         NUMERIC(8,2),
    condition     VARCHAR(20)  NOT NULL,
    listing_type  VARCHAR(20)  NOT NULL,
    description   TEXT,
    status        VARCHAR(20)  NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT listings_condition_valid CHECK (condition    IN ('like_new', 'good', 'fair')),
    CONSTRAINT listings_type_valid      CHECK (listing_type IN ('sale', 'trade', 'giveaway')),
    CONSTRAINT listings_status_valid    CHECK (status       IN ('active', 'sold', 'removed')),
    CONSTRAINT listings_desc_length     CHECK (char_length(description) <= 1000),
    CONSTRAINT listings_price_matches_type CHECK (
        (listing_type =  'sale' AND price IS NOT NULL AND price > 0) OR
        (listing_type <> 'sale' AND price IS NULL)
    )
);

CREATE INDEX idx_listings_course   ON listings (course_id)   WHERE status = 'active';
CREATE INDEX idx_listings_material ON listings (material_id) WHERE status = 'active';
CREATE INDEX idx_listings_isbn     ON listings (isbn)        WHERE status = 'active';
CREATE INDEX idx_listings_seller   ON listings (seller_id);
CREATE INDEX idx_listings_created  ON listings (created_at DESC);


-- ------------------------------------------------------------
-- listing_photos                                          FR-5
--   The five-image limit is enforced in the API, not here.
-- ------------------------------------------------------------
CREATE TABLE listing_photos (
    id             BIGSERIAL    PRIMARY KEY,
    listing_id     BIGINT       NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    url            VARCHAR(500) NOT NULL,
    display_order  SMALLINT     NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_listing_photos_listing ON listing_photos (listing_id, display_order);


-- ------------------------------------------------------------
-- conversations                                          FR-11
--   Scoped to one listing and exactly two participants. One
--   conversation per buyer per listing.
-- ------------------------------------------------------------
CREATE TABLE conversations (
    id          BIGSERIAL   PRIMARY KEY,
    listing_id  BIGINT      NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    buyer_id    BIGINT      NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    seller_id   BIGINT      NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT conversations_unique     UNIQUE (listing_id, buyer_id),
    CONSTRAINT conversations_not_self   CHECK  (buyer_id <> seller_id)
);

CREATE INDEX idx_conversations_buyer  ON conversations (buyer_id);
CREATE INDEX idx_conversations_seller ON conversations (seller_id);


-- ------------------------------------------------------------
-- messages                                               FR-11
-- ------------------------------------------------------------
CREATE TABLE messages (
    id               BIGSERIAL   PRIMARY KEY,
    conversation_id  BIGINT      NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id        BIGINT      NOT NULL REFERENCES users(id)         ON DELETE CASCADE,
    body             TEXT        NOT NULL,
    sent_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at          TIMESTAMPTZ,

    CONSTRAINT messages_body_length CHECK (char_length(body) BETWEEN 1 AND 2000)
);

CREATE INDEX idx_messages_conversation ON messages (conversation_id, sent_at);


-- ------------------------------------------------------------
-- watchlists                                             FR-12
--   The unique constraint is what prevents duplicate alerts.
-- ------------------------------------------------------------
CREATE TABLE watchlists (
    id           BIGSERIAL   PRIMARY KEY,
    user_id      BIGINT      NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    material_id  BIGINT      NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT watchlists_unique UNIQUE (user_id, material_id)
);

CREATE INDEX idx_watchlists_material ON watchlists (material_id);


-- ------------------------------------------------------------
-- notifications                                          FR-13
--   Records alerts already sent, so a student is never emailed
--   twice about the same listing.
-- ------------------------------------------------------------
CREATE TABLE notifications (
    id          BIGSERIAL   PRIMARY KEY,
    user_id     BIGINT      NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    listing_id  BIGINT      NOT NULL REFERENCES listings(id)  ON DELETE CASCADE,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT notifications_unique UNIQUE (user_id, listing_id)
);


-- ------------------------------------------------------------
-- meetup_locations                                       FR-18
--   Stored as data so the list changes without a code change.
-- ------------------------------------------------------------
CREATE TABLE meetup_locations (
    id        BIGSERIAL    PRIMARY KEY,
    name      VARCHAR(150) NOT NULL,
    building  VARCHAR(150),
    active    BOOLEAN      NOT NULL DEFAULT TRUE
);


-- ============================================================
--  SEED DATA
--  Enough to demonstrate search and the budget planner.
-- ============================================================

INSERT INTO meetup_locations (name, building) VALUES
  ('University Union, first floor',   'University Union'),
  ('Willis Library entrance',         'Willis Library'),
  ('Discovery Park atrium',           'Discovery Park'),
  ('Business Leadership Building lobby', 'BLB'),
  ('Pohl Recreation Center entrance', 'Pohl Rec Center');

INSERT INTO courses (course_number, title, department) VALUES
  ('ACCT 2010', 'Principles of Accounting I',        'Accounting'),
  ('ACCT 2020', 'Principles of Accounting II',       'Accounting'),
  ('BIOL 1710', 'Biology for Science Majors I',      'Biological Sciences'),
  ('BIOL 1760', 'Biology for Science Majors II',     'Biological Sciences'),
  ('CHEM 1410', 'General Chemistry I',               'Chemistry'),
  ('CSCE 1030', 'Computer Science I',                'Computer Science and Engineering'),
  ('CSCE 3444', 'Software Engineering',              'Computer Science and Engineering'),
  ('ECON 1100', 'Principles of Macroeconomics',      'Economics'),
  ('ENGL 1310', 'College Writing I',                 'English'),
  ('HIST 2610', 'United States History to 1865',     'History'),
  ('MATH 1710', 'Calculus I',                        'Mathematics'),
  ('PSYC 1630', 'General Psychology',                'Psychology');

INSERT INTO materials (title, author, edition, isbn, retail_price, transferable) VALUES
  ('Financial Accounting',               'Weygandt, Kimmel, Kieso', '12th', '9781119594611', 189.00, TRUE),
  ('Managerial Accounting',              'Weygandt, Kimmel, Kieso', '9th',  '9781119709589', 175.00, TRUE),
  ('Campbell Biology',                   'Urry, Cain, Wasserman',   '12th', '9780135188743', 199.00, TRUE),
  ('Biology Laboratory Manual',          'Vodopich, Moore',         '12th', '9781260200720',  44.00, TRUE),
  ('Chemistry: The Central Science',     'Brown, LeMay, Bursten',   '15th', '9780137493701', 210.00, TRUE),
  ('C++ How to Program',                 'Deitel and Deitel',       '10th', '9780134448237', 165.00, TRUE),
  ('Software Engineering: A Practitioner''s Approach', 'Pressman, Maxim', '9th', '9781259872976', 155.00, TRUE),
  ('Principles of Macroeconomics',       'Mankiw',                  '9th',  '9780357133491', 180.00, TRUE),
  ('They Say / I Say',                   'Graff, Birkenstein',      '6th',  '9781324070047',  40.00, TRUE),
  ('Give Me Liberty! An American History','Foner',                  '7th',  '9780393878172',  55.00, TRUE),
  ('Calculus: Early Transcendentals',    'Stewart',                 '9th',  '9781337613927', 230.00, TRUE),
  ('WebAssign access code (MATH 1710)',  NULL,                      NULL,   NULL,            125.00, FALSE),
  ('Psychology',                         'Myers, DeWall',           '13th', '9781319132101', 160.00, TRUE),
  ('Pearson MyLab access code (PSYC 1630)', NULL,                   NULL,   NULL,             95.00, FALSE);

-- Map materials to courses by looking them up, so this stays
-- correct regardless of the IDs the serial sequence assigned.
INSERT INTO course_materials (course_id, material_id, required)
SELECT c.id, m.id, TRUE
FROM   (VALUES
          ('ACCT 2010', '9781119594611'),
          ('ACCT 2020', '9781119709589'),
          ('BIOL 1710', '9780135188743'),
          ('BIOL 1710', '9781260200720'),
          ('BIOL 1760', '9780135188743'),
          ('CHEM 1410', '9780137493701'),
          ('CSCE 1030', '9780134448237'),
          ('CSCE 3444', '9781259872976'),
          ('ECON 1100', '9780357133491'),
          ('ENGL 1310', '9781324070047'),
          ('HIST 2610', '9780393878172'),
          ('MATH 1710', '9781337613927'),
          ('PSYC 1630', '9781319132101')
       ) AS pair(course_number, isbn)
JOIN   courses   c ON c.course_number = pair.course_number
JOIN   materials m ON m.isbn          = pair.isbn;

-- The two access codes have no ISBN, so they are mapped by title.
INSERT INTO course_materials (course_id, material_id, required)
SELECT c.id, m.id, TRUE
FROM   courses c, materials m
WHERE  c.course_number = 'MATH 1710'
  AND  m.title = 'WebAssign access code (MATH 1710)';

INSERT INTO course_materials (course_id, material_id, required)
SELECT c.id, m.id, TRUE
FROM   courses c, materials m
WHERE  c.course_number = 'PSYC 1630'
  AND  m.title = 'Pearson MyLab access code (PSYC 1630)';

-- CHEM 1410 is deliberately left with only one material and
-- ENGL 1310 with one, so you can test the "partial data" path.
-- No materials are mapped to ACCT 2020's lab, giving you a
-- course that exercises the "unknown" branch in FR-15.
