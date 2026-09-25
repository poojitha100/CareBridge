from flask import Flask, render_template, request, redirect, url_for, flash
import os
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)


# =========================================================
# Flask Secret Key
# =========================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "carebridge-secret-key"
)


# =========================================================
# Database Connection
# =========================================================

def get_db_connection():
    database_url = os.environ.get("NEON_DATABASE_URL")

    if not database_url:
        raise Exception("NEON_DATABASE_URL is not configured")

    return psycopg2.connect(database_url)


# =========================================================
# Generate Next Patient ID
# =========================================================

def get_next_patient_id(cursor):

    cursor.execute("""
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTRING(patient_id FROM 2) AS INTEGER
                )
            ),
            1000
        )
        FROM users
        WHERE patient_id LIKE 'P%'
    """)

    last_number = cursor.fetchone()[0]

    next_number = last_number + 1

    return f"P{next_number}"


# =========================================================
# Landing Page
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# Patient Login
# Login using Mobile Number + Date of Birth
# =========================================================

@app.route("/patient-login", methods=["GET", "POST"])
def patient_login():

    # -----------------------------------------------------
    # Open Login Page
    # -----------------------------------------------------

    if request.method == "GET":
        return render_template("patient_login.html")


    # -----------------------------------------------------
    # Get Login Form Data
    # -----------------------------------------------------

    phone_number = request.form.get(
        "phone",
        ""
    ).strip()

    dob = request.form.get(
        "dob",
        ""
    ).strip()


    # -----------------------------------------------------
    # Validate Mobile Number
    # -----------------------------------------------------

    if not phone_number:

        flash(
            "Please enter your registered mobile number.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    # -----------------------------------------------------
    # Validate Date of Birth
    # -----------------------------------------------------

    if not dob:

        flash(
            "Please enter your date of birth.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    connection = None
    cursor = None


    try:

        connection = get_db_connection()

        cursor = connection.cursor()


        # -------------------------------------------------
        # Find Patient
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT patient_id, full_name
            FROM users
            WHERE phone_number = %s
              AND dob = %s
              AND account_status = 'Active'
            LIMIT 1
            """,
            (
                phone_number,
                dob
            )
        )


        patient = cursor.fetchone()


        # -------------------------------------------------
        # Invalid Login
        # -------------------------------------------------

        if not patient:

            flash(
                "Mobile number or date of birth is incorrect.",
                "error"
            )

            return redirect(
                url_for("patient_login")
            )


        # -------------------------------------------------
        # Patient Found
        # -------------------------------------------------

        patient_id = patient[0]


        # -------------------------------------------------
        # Redirect to Patient Home
        # -------------------------------------------------

        return redirect(
            url_for(
                "patient_dashboard",
                patient_id=patient_id
            )
        )


    except Exception as e:

        print(
            "Login Error:",
            e
        )

        flash(
            "Something went wrong. Please try again.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# Signup Success Page
# =========================================================

@app.route("/signup-success")
def signup_success():

    patient_id = request.args.get(
        "patient_id"
    )


    if not patient_id:

        return redirect(
            url_for("signup")
        )


    return render_template(
        "signup_success.html",
        patient_id=patient_id
    )


# =========================================================
# Patient Signup
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    # -----------------------------------------------------
    # GET REQUEST
    # -----------------------------------------------------

    if request.method == "GET":

        return render_template(
            "signup.html",
            next_patient_id="Auto Generated"
        )


    # -----------------------------------------------------
    # Get Form Data
    # -----------------------------------------------------

    full_name = request.form.get(
        "full_name",
        ""
    ).strip()


    dob = request.form.get(
        "date_of_birth",
        ""
    ).strip()


    gender = request.form.get(
        "gender",
        ""
    ).strip()


    phone_number = request.form.get(
        "phone",
        ""
    ).strip()


    email = request.form.get(
        "email",
        ""
    ).strip()


    emergency_contact = request.form.get(
        "emergency_contact",
        ""
    ).strip()


    address = request.form.get(
        "address",
        ""
    ).strip()


    password = request.form.get(
        "password",
        ""
    )


    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    # =====================================================
    # Form Validation
    # =====================================================

    if not full_name:

        flash(
            "Please enter your full name.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not dob:

        flash(
            "Please select your date of birth.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not gender:

        flash(
            "Please select your gender.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not phone_number:

        flash(
            "Please enter your phone number.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not emergency_contact:

        flash(
            "Please enter your emergency contact number.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not address:

        flash(
            "Please enter your address.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not password:

        flash(
            "Please create a password.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if not confirm_password:

        flash(
            "Please confirm your password.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return redirect(
            url_for("signup")
        )


    connection = None
    cursor = None


    try:

        connection = get_db_connection()

        cursor = connection.cursor()


        # =================================================
        # Check Existing Phone Number
        # =================================================

        cursor.execute(
            """
            SELECT patient_id
            FROM users
            WHERE phone_number = %s
            LIMIT 1
            """,
            (phone_number,)
        )


        existing_phone = cursor.fetchone()


        if existing_phone:

            flash(
                "An account with this phone number already exists.",
                "error"
            )

            return redirect(
                url_for("signup")
            )


        # =================================================
        # Check Existing Email
        # Only if Email was entered
        # =================================================

        if email:

            cursor.execute(
                """
                SELECT patient_id
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )


            existing_email = cursor.fetchone()


            if existing_email:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return redirect(
                    url_for("signup")
                )


        # =================================================
        # Generate Patient ID
        # =================================================

        patient_id = get_next_patient_id(
            cursor
        )


        # =================================================
        # Hash Password
        # =================================================

        hashed_password = generate_password_hash(
            password
        )


        # =================================================
        # Insert Patient Into Database
        # =================================================

        cursor.execute(
            """
            INSERT INTO users
            (
                patient_id,
                full_name,
                dob,
                gender,
                phone_number,
                email,
                password,
                emergency_contact,
                address,
                account_status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                patient_id,
                full_name,
                dob,
                gender,
                phone_number,
                email if email else None,
                hashed_password,
                emergency_contact,
                address,
                "Active"
            )
        )


        # =================================================
        # Save Changes
        # =================================================

        connection.commit()


        # =================================================
        # Go To Success Page
        # =================================================

        return redirect(
            url_for(
                "signup_success",
                patient_id=patient_id
            )
        )


    except Exception as e:

        if connection:

            connection.rollback()


        print(
            "Signup Error:",
            e
        )


        flash(
            "Something went wrong while creating your account.",
            "error"
        )


        return redirect(
            url_for("signup")
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# Patient Dashboard / Home
# =========================================================

@app.route("/patient-dashboard")
def patient_dashboard():

    # -----------------------------------------------------
    # Get Patient ID
    # -----------------------------------------------------

    patient_id = request.args.get(
        "patient_id"
    )


    # -----------------------------------------------------
    # If Patient ID Missing
    # -----------------------------------------------------

    if not patient_id:

        return redirect(
            url_for("patient_login")
        )


    connection = None
    cursor = None


    try:

        connection = get_db_connection()

        cursor = connection.cursor()


        # -------------------------------------------------
        # Get Patient Details
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT patient_id, full_name
            FROM users
            WHERE patient_id = %s
              AND account_status = 'Active'
            LIMIT 1
            """,
            (patient_id,)
        )


        patient = cursor.fetchone()


        # -------------------------------------------------
        # Patient Not Found
        # -------------------------------------------------

        if not patient:

            flash(
                "Patient account not found.",
                "error"
            )

            return redirect(
                url_for("patient_login")
            )


        # -------------------------------------------------
        # Patient Details
        # -------------------------------------------------

        patient_id = patient[0]

        patient_name = patient[1]


        # -------------------------------------------------
        # Open Patient Home
        # -------------------------------------------------

        return render_template(
            "home.html",
            patient_id=patient_id,
            patient_name=patient_name
        )


    except Exception as e:

        print(
            "Patient Dashboard Error:",
            e
        )


        flash(
            "Something went wrong. Please try again.",
            "error"
        )


        return redirect(
            url_for("patient_login")
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()
# =========================================================
# Book Appointment Page
# =========================================================

@app.route("/book-appointment")
def book_appointment():

    patient_id = request.args.get("patient_id")

    if not patient_id:
        return redirect(url_for("patient_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT patient_id, full_name
            FROM users
            WHERE patient_id = %s
              AND account_status = 'Active'
            LIMIT 1
            """,
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:
            return redirect(url_for("patient_login"))

        return render_template(
            "appointment.html",
            patient_id=patient[0],
            patient_name=patient[1]
        )

    except Exception as e:

        print("Appointment Page Error:", e)

        flash(
            "Something went wrong. Please try again.",
            "error"
        )

        return redirect(
            url_for(
                "patient_dashboard",
                patient_id=patient_id
            )
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()



# =========================================================
# Confirm Appointment
# =========================================================

# =========================================================
# Confirm Appointment
# =========================================================

@app.route("/confirm-appointment", methods=["POST"])
def confirm_appointment():

    patient_id = request.form.get(
        "patient_id",
        ""
    ).strip()

    if not patient_id:
        return redirect(
            url_for("patient_login")
        )

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        # -------------------------------------------------
        # Get Patient Details
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT user_id, patient_id, full_name
            FROM users
            WHERE patient_id = %s
              AND account_status = 'Active'
            LIMIT 1
            """,
            (patient_id,)
        )

        patient = cursor.fetchone()

        if not patient:

            flash(
                "Patient account not found.",
                "error"
            )

            return redirect(
                url_for("patient_login")
            )

        user_id = patient[0]
        patient_id = patient[1]
        patient_name = patient[2]

        # -------------------------------------------------
        # Check if Patient Already Has Appointment Today
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT appointment_token
            FROM appointments
            WHERE user_id = %s
              AND booking_date = CURRENT_DATE
            LIMIT 1
            """,
            (user_id,)
        )

        existing_appointment = cursor.fetchone()

        if existing_appointment:

            booking_number = (
                f"A{existing_appointment[0]:03d}"
            )

            return render_template(
                "appointment_confirmation.html",
                patient_id=patient_id,
                patient_name=patient_name,
                booking_number=booking_number
            )

        # -------------------------------------------------
        # Get Today's Last Appointment Token
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COALESCE(
                MAX(appointment_token),
                0
            )
            FROM appointments
            WHERE booking_date = CURRENT_DATE
            """
        )

        last_number = cursor.fetchone()[0]

        # -------------------------------------------------
        # Generate Next Number
        # -------------------------------------------------

        next_number = last_number + 1

        # Database stores:
        # 1, 2, 3...
        #
        # Screen displays:
        # A001, A002, A003...

        booking_number = f"A{next_number:03d}"

        # -------------------------------------------------
        # Insert Appointment
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO appointments
            (
                user_id,
                appointment_token,
                booking_date,
                booking_time,
                appointment_status
            )
            VALUES
            (
                %s,
                %s,
                CURRENT_DATE,
                CURRENT_TIME,
                %s
            )
            """,
            (
                user_id,
                next_number,
                "Booked"
            )
        )

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        connection.commit()

        # -------------------------------------------------
        # Open Confirmation Page
        # -------------------------------------------------

        return render_template(
            "appointment_confirmation.html",
            patient_id=patient_id,
            patient_name=patient_name,
            booking_number=booking_number
        )

    except Exception as e:

        if connection:
            connection.rollback()

        print(
            "Confirm Appointment Error:",
            e
        )

        flash(
            "Something went wrong while booking the appointment.",
            "error"
        )

        return redirect(
            url_for(
                "book_appointment",
                patient_id=patient_id
            )
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


            
# =========================================================
# Receptionist Dashboard
# =========================================================

# =========================================================
# Receptionist Dashboard
# =========================================================

@app.route("/receptionist-dashboard")
def receptionist_dashboard():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        # -----------------------------------------
        # Get Today's Appointments
        # -----------------------------------------

        cursor.execute(
            """
            SELECT
                a.appointment_id,
                u.patient_id,
                u.full_name,
                a.appointment_token,
                a.appointment_status
            FROM appointments AS a
            JOIN users AS u
                ON a.user_id = u.user_id
            WHERE a.booking_date::date = CURRENT_DATE
            ORDER BY a.appointment_token ASC
            """
        )

        appointments = cursor.fetchall()

        print("TODAY APPOINTMENTS:", appointments)


        # -----------------------------------------
        # Today's Appointment Count
        # -----------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE booking_date::date = CURRENT_DATE
            """
        )

        today_count = cursor.fetchone()[0]

        print("TODAY COUNT:", today_count)


        # -----------------------------------------
        # Verified Count
        # -----------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE booking_date::date = CURRENT_DATE
              AND appointment_status = 'Verified'
            """
        )

        verified_count = cursor.fetchone()[0]


        # -----------------------------------------
        # OP Token Count
        # -----------------------------------------

        token_count = 0


        # -----------------------------------------
        # Open Dashboard
        # -----------------------------------------

        return render_template(
            "receptionist_dashboard.html",
            appointments=appointments,
            today_count=today_count,
            verified_count=verified_count,
            token_count=token_count
        )


    except Exception as e:

        print("RECEPTIONIST DASHBOARD ERROR:", e)

        if connection:
            connection.rollback()

        return render_template(
            "receptionist_dashboard.html",
            appointments=[],
            today_count=0,
            verified_count=0,
            token_count=0
        )


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/verify-patient/<int:appointment_id>")
def verify_patient(appointment_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
            a.appointment_id,
                    a.appointment_token,
                    a.booking_date,
                    a.booking_time,
                    a.appointment_status,
                    u.patient_id,
                    u.full_name,
                    u.phone,
                    u.date_of_birth,
                    u.gender,
                    u.address,
                    u.emergency_contact
                FROM appointments AS a
                JOIN users AS u
                    ON a.user_id = u.user_id
                WHERE a.appointment_id = %s
                LIMIT 1
                """,
                (appointment_id,)
        )
        patient = cursor.fetchone()

        if not patient:
            flash("Appointment not found.", "error")
            return redirect(url_for("receptionist_dashboard"))

        return render_template(
            "verify_patient.html",
            patient=patient
        )

    except Exception as e:


        print("Verify Patient Error:", e)

        if connection:
            connection.rollback()

        flash("Something went wrong while loading patient details.", "error")

        return redirect(url_for("receptionist_dashboard"))

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()



            

@app.route("/receptionist-login", methods=["GET", "POST"])
def receptionist_login():

    if request.method == "GET":
        return render_template("receptionist_login.html")

    receptionist_login_id = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not receptionist_login_id or not password:
        flash(
            "Please enter your username/Receptionist ID and password.",
            "error"
        )
        return redirect(url_for("receptionist_login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                receptionist_id,
                receptionist_code,
                full_name,
                password,
                account_status
            FROM receptionists
            WHERE (receptionist_code = %s
                   OR CAST(receptionist_id AS TEXT) = %s)
              AND account_status = 'Active'
            LIMIT 1
            """,
            (receptionist_login_id, receptionist_login_id)
        )

        receptionist = cursor.fetchone()

        if not receptionist:
            flash(
                "Invalid receptionist ID or password.",
                "error"
            )
            return redirect(url_for("receptionist_login"))

        receptionist_id = receptionist[0]
        receptionist_code = receptionist[1]
        receptionist_name = receptionist[2]
        stored_password = receptionist[3]

        # Current database stores the password as plain text.
        password_valid = (stored_password == password)

        if not password_valid:
            flash(
                "Invalid receptionist ID or password.",
                "error"
            )
            return redirect(url_for("receptionist_login"))

        return redirect(url_for("receptionist_dashboard"))

    except Exception as e:

        if connection:
            connection.rollback()

        flash(
            "Something went wrong during login.",
            "error"
        )

        return redirect(url_for("receptionist_login"))

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()
# =========================================================
# Run Flask Application
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=81
    )