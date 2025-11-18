package com.smsclassifier.app.data;

import android.database.Cursor;
import android.os.CancellationSignal;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.paging.PagingSource;
import androidx.room.CoroutinesRoom;
import androidx.room.EntityDeletionOrUpdateAdapter;
import androidx.room.EntityInsertionAdapter;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.SharedSQLiteStatement;
import androidx.room.paging.LimitOffsetPagingSource;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import androidx.sqlite.db.SupportSQLiteStatement;
import java.lang.Boolean;
import java.lang.Class;
import java.lang.Exception;
import java.lang.Float;
import java.lang.Integer;
import java.lang.Long;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Callable;
import javax.annotation.processing.Generated;
import kotlin.Unit;
import kotlin.coroutines.Continuation;
import kotlinx.coroutines.flow.Flow;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class MessageDao_Impl implements MessageDao {
  private final RoomDatabase __db;

  private final EntityInsertionAdapter<MessageEntity> __insertionAdapterOfMessageEntity;

  private final EntityDeletionOrUpdateAdapter<MessageEntity> __updateAdapterOfMessageEntity;

  private final SharedSQLiteStatement __preparedStmtOfMarkReviewed;

  private final SharedSQLiteStatement __preparedStmtOfDelete;

  public MessageDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
    this.__insertionAdapterOfMessageEntity = new EntityInsertionAdapter<MessageEntity>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "INSERT OR REPLACE INTO `messages` (`id`,`sender`,`body`,`ts`,`language`,`featuresJson`,`isOtp`,`otpIntent`,`isPhishing`,`phishScore`,`reasonsJson`,`reviewed`,`version`) VALUES (nullif(?, 0),?,?,?,?,?,?,?,?,?,?,?,?)";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final MessageEntity entity) {
        statement.bindLong(1, entity.getId());
        statement.bindString(2, entity.getSender());
        statement.bindString(3, entity.getBody());
        statement.bindLong(4, entity.getTs());
        if (entity.getLanguage() == null) {
          statement.bindNull(5);
        } else {
          statement.bindString(5, entity.getLanguage());
        }
        if (entity.getFeaturesJson() == null) {
          statement.bindNull(6);
        } else {
          statement.bindString(6, entity.getFeaturesJson());
        }
        final Integer _tmp = entity.isOtp() == null ? null : (entity.isOtp() ? 1 : 0);
        if (_tmp == null) {
          statement.bindNull(7);
        } else {
          statement.bindLong(7, _tmp);
        }
        if (entity.getOtpIntent() == null) {
          statement.bindNull(8);
        } else {
          statement.bindString(8, entity.getOtpIntent());
        }
        final Integer _tmp_1 = entity.isPhishing() == null ? null : (entity.isPhishing() ? 1 : 0);
        if (_tmp_1 == null) {
          statement.bindNull(9);
        } else {
          statement.bindLong(9, _tmp_1);
        }
        if (entity.getPhishScore() == null) {
          statement.bindNull(10);
        } else {
          statement.bindDouble(10, entity.getPhishScore());
        }
        if (entity.getReasonsJson() == null) {
          statement.bindNull(11);
        } else {
          statement.bindString(11, entity.getReasonsJson());
        }
        final int _tmp_2 = entity.getReviewed() ? 1 : 0;
        statement.bindLong(12, _tmp_2);
        statement.bindLong(13, entity.getVersion());
      }
    };
    this.__updateAdapterOfMessageEntity = new EntityDeletionOrUpdateAdapter<MessageEntity>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "UPDATE OR ABORT `messages` SET `id` = ?,`sender` = ?,`body` = ?,`ts` = ?,`language` = ?,`featuresJson` = ?,`isOtp` = ?,`otpIntent` = ?,`isPhishing` = ?,`phishScore` = ?,`reasonsJson` = ?,`reviewed` = ?,`version` = ? WHERE `id` = ?";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final MessageEntity entity) {
        statement.bindLong(1, entity.getId());
        statement.bindString(2, entity.getSender());
        statement.bindString(3, entity.getBody());
        statement.bindLong(4, entity.getTs());
        if (entity.getLanguage() == null) {
          statement.bindNull(5);
        } else {
          statement.bindString(5, entity.getLanguage());
        }
        if (entity.getFeaturesJson() == null) {
          statement.bindNull(6);
        } else {
          statement.bindString(6, entity.getFeaturesJson());
        }
        final Integer _tmp = entity.isOtp() == null ? null : (entity.isOtp() ? 1 : 0);
        if (_tmp == null) {
          statement.bindNull(7);
        } else {
          statement.bindLong(7, _tmp);
        }
        if (entity.getOtpIntent() == null) {
          statement.bindNull(8);
        } else {
          statement.bindString(8, entity.getOtpIntent());
        }
        final Integer _tmp_1 = entity.isPhishing() == null ? null : (entity.isPhishing() ? 1 : 0);
        if (_tmp_1 == null) {
          statement.bindNull(9);
        } else {
          statement.bindLong(9, _tmp_1);
        }
        if (entity.getPhishScore() == null) {
          statement.bindNull(10);
        } else {
          statement.bindDouble(10, entity.getPhishScore());
        }
        if (entity.getReasonsJson() == null) {
          statement.bindNull(11);
        } else {
          statement.bindString(11, entity.getReasonsJson());
        }
        final int _tmp_2 = entity.getReviewed() ? 1 : 0;
        statement.bindLong(12, _tmp_2);
        statement.bindLong(13, entity.getVersion());
        statement.bindLong(14, entity.getId());
      }
    };
    this.__preparedStmtOfMarkReviewed = new SharedSQLiteStatement(__db) {
      @Override
      @NonNull
      public String createQuery() {
        final String _query = "UPDATE messages SET reviewed = 1 WHERE id = ?";
        return _query;
      }
    };
    this.__preparedStmtOfDelete = new SharedSQLiteStatement(__db) {
      @Override
      @NonNull
      public String createQuery() {
        final String _query = "DELETE FROM messages WHERE id = ?";
        return _query;
      }
    };
  }

  @Override
  public Object insert(final MessageEntity message, final Continuation<? super Long> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Long>() {
      @Override
      @NonNull
      public Long call() throws Exception {
        __db.beginTransaction();
        try {
          final Long _result = __insertionAdapterOfMessageEntity.insertAndReturnId(message);
          __db.setTransactionSuccessful();
          return _result;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object update(final MessageEntity message, final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        __db.beginTransaction();
        try {
          __updateAdapterOfMessageEntity.handle(message);
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object markReviewed(final long id, final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        final SupportSQLiteStatement _stmt = __preparedStmtOfMarkReviewed.acquire();
        int _argIndex = 1;
        _stmt.bindLong(_argIndex, id);
        try {
          __db.beginTransaction();
          try {
            _stmt.executeUpdateDelete();
            __db.setTransactionSuccessful();
            return Unit.INSTANCE;
          } finally {
            __db.endTransaction();
          }
        } finally {
          __preparedStmtOfMarkReviewed.release(_stmt);
        }
      }
    }, $completion);
  }

  @Override
  public Object delete(final long id, final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        final SupportSQLiteStatement _stmt = __preparedStmtOfDelete.acquire();
        int _argIndex = 1;
        _stmt.bindLong(_argIndex, id);
        try {
          __db.beginTransaction();
          try {
            _stmt.executeUpdateDelete();
            __db.setTransactionSuccessful();
            return Unit.INSTANCE;
          } finally {
            __db.endTransaction();
          }
        } finally {
          __preparedStmtOfDelete.release(_stmt);
        }
      }
    }, $completion);
  }

  @Override
  public PagingSource<Integer, MessageEntity> getAllPaged() {
    final String _sql = "SELECT * FROM messages ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return new LimitOffsetPagingSource<MessageEntity>(_statement, __db, "messages") {
      @Override
      @NonNull
      protected List<MessageEntity> convertRows(@NonNull final Cursor cursor) {
        final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(cursor, "id");
        final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(cursor, "sender");
        final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(cursor, "body");
        final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(cursor, "ts");
        final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(cursor, "language");
        final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(cursor, "featuresJson");
        final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(cursor, "isOtp");
        final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(cursor, "otpIntent");
        final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(cursor, "isPhishing");
        final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(cursor, "phishScore");
        final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(cursor, "reasonsJson");
        final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(cursor, "reviewed");
        final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(cursor, "version");
        final List<MessageEntity> _result = new ArrayList<MessageEntity>(cursor.getCount());
        while (cursor.moveToNext()) {
          final MessageEntity _item;
          final long _tmpId;
          _tmpId = cursor.getLong(_cursorIndexOfId);
          final String _tmpSender;
          _tmpSender = cursor.getString(_cursorIndexOfSender);
          final String _tmpBody;
          _tmpBody = cursor.getString(_cursorIndexOfBody);
          final long _tmpTs;
          _tmpTs = cursor.getLong(_cursorIndexOfTs);
          final String _tmpLanguage;
          if (cursor.isNull(_cursorIndexOfLanguage)) {
            _tmpLanguage = null;
          } else {
            _tmpLanguage = cursor.getString(_cursorIndexOfLanguage);
          }
          final String _tmpFeaturesJson;
          if (cursor.isNull(_cursorIndexOfFeaturesJson)) {
            _tmpFeaturesJson = null;
          } else {
            _tmpFeaturesJson = cursor.getString(_cursorIndexOfFeaturesJson);
          }
          final Boolean _tmpIsOtp;
          final Integer _tmp;
          if (cursor.isNull(_cursorIndexOfIsOtp)) {
            _tmp = null;
          } else {
            _tmp = cursor.getInt(_cursorIndexOfIsOtp);
          }
          _tmpIsOtp = _tmp == null ? null : _tmp != 0;
          final String _tmpOtpIntent;
          if (cursor.isNull(_cursorIndexOfOtpIntent)) {
            _tmpOtpIntent = null;
          } else {
            _tmpOtpIntent = cursor.getString(_cursorIndexOfOtpIntent);
          }
          final Boolean _tmpIsPhishing;
          final Integer _tmp_1;
          if (cursor.isNull(_cursorIndexOfIsPhishing)) {
            _tmp_1 = null;
          } else {
            _tmp_1 = cursor.getInt(_cursorIndexOfIsPhishing);
          }
          _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
          final Float _tmpPhishScore;
          if (cursor.isNull(_cursorIndexOfPhishScore)) {
            _tmpPhishScore = null;
          } else {
            _tmpPhishScore = cursor.getFloat(_cursorIndexOfPhishScore);
          }
          final String _tmpReasonsJson;
          if (cursor.isNull(_cursorIndexOfReasonsJson)) {
            _tmpReasonsJson = null;
          } else {
            _tmpReasonsJson = cursor.getString(_cursorIndexOfReasonsJson);
          }
          final boolean _tmpReviewed;
          final int _tmp_2;
          _tmp_2 = cursor.getInt(_cursorIndexOfReviewed);
          _tmpReviewed = _tmp_2 != 0;
          final int _tmpVersion;
          _tmpVersion = cursor.getInt(_cursorIndexOfVersion);
          _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          _result.add(_item);
        }
        return _result;
      }
    };
  }

  @Override
  public PagingSource<Integer, MessageEntity> getOtpPaged() {
    final String _sql = "SELECT * FROM messages WHERE isOtp = 1 ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return new LimitOffsetPagingSource<MessageEntity>(_statement, __db, "messages") {
      @Override
      @NonNull
      protected List<MessageEntity> convertRows(@NonNull final Cursor cursor) {
        final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(cursor, "id");
        final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(cursor, "sender");
        final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(cursor, "body");
        final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(cursor, "ts");
        final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(cursor, "language");
        final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(cursor, "featuresJson");
        final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(cursor, "isOtp");
        final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(cursor, "otpIntent");
        final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(cursor, "isPhishing");
        final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(cursor, "phishScore");
        final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(cursor, "reasonsJson");
        final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(cursor, "reviewed");
        final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(cursor, "version");
        final List<MessageEntity> _result = new ArrayList<MessageEntity>(cursor.getCount());
        while (cursor.moveToNext()) {
          final MessageEntity _item;
          final long _tmpId;
          _tmpId = cursor.getLong(_cursorIndexOfId);
          final String _tmpSender;
          _tmpSender = cursor.getString(_cursorIndexOfSender);
          final String _tmpBody;
          _tmpBody = cursor.getString(_cursorIndexOfBody);
          final long _tmpTs;
          _tmpTs = cursor.getLong(_cursorIndexOfTs);
          final String _tmpLanguage;
          if (cursor.isNull(_cursorIndexOfLanguage)) {
            _tmpLanguage = null;
          } else {
            _tmpLanguage = cursor.getString(_cursorIndexOfLanguage);
          }
          final String _tmpFeaturesJson;
          if (cursor.isNull(_cursorIndexOfFeaturesJson)) {
            _tmpFeaturesJson = null;
          } else {
            _tmpFeaturesJson = cursor.getString(_cursorIndexOfFeaturesJson);
          }
          final Boolean _tmpIsOtp;
          final Integer _tmp;
          if (cursor.isNull(_cursorIndexOfIsOtp)) {
            _tmp = null;
          } else {
            _tmp = cursor.getInt(_cursorIndexOfIsOtp);
          }
          _tmpIsOtp = _tmp == null ? null : _tmp != 0;
          final String _tmpOtpIntent;
          if (cursor.isNull(_cursorIndexOfOtpIntent)) {
            _tmpOtpIntent = null;
          } else {
            _tmpOtpIntent = cursor.getString(_cursorIndexOfOtpIntent);
          }
          final Boolean _tmpIsPhishing;
          final Integer _tmp_1;
          if (cursor.isNull(_cursorIndexOfIsPhishing)) {
            _tmp_1 = null;
          } else {
            _tmp_1 = cursor.getInt(_cursorIndexOfIsPhishing);
          }
          _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
          final Float _tmpPhishScore;
          if (cursor.isNull(_cursorIndexOfPhishScore)) {
            _tmpPhishScore = null;
          } else {
            _tmpPhishScore = cursor.getFloat(_cursorIndexOfPhishScore);
          }
          final String _tmpReasonsJson;
          if (cursor.isNull(_cursorIndexOfReasonsJson)) {
            _tmpReasonsJson = null;
          } else {
            _tmpReasonsJson = cursor.getString(_cursorIndexOfReasonsJson);
          }
          final boolean _tmpReviewed;
          final int _tmp_2;
          _tmp_2 = cursor.getInt(_cursorIndexOfReviewed);
          _tmpReviewed = _tmp_2 != 0;
          final int _tmpVersion;
          _tmpVersion = cursor.getInt(_cursorIndexOfVersion);
          _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          _result.add(_item);
        }
        return _result;
      }
    };
  }

  @Override
  public PagingSource<Integer, MessageEntity> getPhishingPaged() {
    final String _sql = "SELECT * FROM messages WHERE isPhishing = 1 ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return new LimitOffsetPagingSource<MessageEntity>(_statement, __db, "messages") {
      @Override
      @NonNull
      protected List<MessageEntity> convertRows(@NonNull final Cursor cursor) {
        final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(cursor, "id");
        final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(cursor, "sender");
        final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(cursor, "body");
        final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(cursor, "ts");
        final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(cursor, "language");
        final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(cursor, "featuresJson");
        final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(cursor, "isOtp");
        final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(cursor, "otpIntent");
        final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(cursor, "isPhishing");
        final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(cursor, "phishScore");
        final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(cursor, "reasonsJson");
        final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(cursor, "reviewed");
        final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(cursor, "version");
        final List<MessageEntity> _result = new ArrayList<MessageEntity>(cursor.getCount());
        while (cursor.moveToNext()) {
          final MessageEntity _item;
          final long _tmpId;
          _tmpId = cursor.getLong(_cursorIndexOfId);
          final String _tmpSender;
          _tmpSender = cursor.getString(_cursorIndexOfSender);
          final String _tmpBody;
          _tmpBody = cursor.getString(_cursorIndexOfBody);
          final long _tmpTs;
          _tmpTs = cursor.getLong(_cursorIndexOfTs);
          final String _tmpLanguage;
          if (cursor.isNull(_cursorIndexOfLanguage)) {
            _tmpLanguage = null;
          } else {
            _tmpLanguage = cursor.getString(_cursorIndexOfLanguage);
          }
          final String _tmpFeaturesJson;
          if (cursor.isNull(_cursorIndexOfFeaturesJson)) {
            _tmpFeaturesJson = null;
          } else {
            _tmpFeaturesJson = cursor.getString(_cursorIndexOfFeaturesJson);
          }
          final Boolean _tmpIsOtp;
          final Integer _tmp;
          if (cursor.isNull(_cursorIndexOfIsOtp)) {
            _tmp = null;
          } else {
            _tmp = cursor.getInt(_cursorIndexOfIsOtp);
          }
          _tmpIsOtp = _tmp == null ? null : _tmp != 0;
          final String _tmpOtpIntent;
          if (cursor.isNull(_cursorIndexOfOtpIntent)) {
            _tmpOtpIntent = null;
          } else {
            _tmpOtpIntent = cursor.getString(_cursorIndexOfOtpIntent);
          }
          final Boolean _tmpIsPhishing;
          final Integer _tmp_1;
          if (cursor.isNull(_cursorIndexOfIsPhishing)) {
            _tmp_1 = null;
          } else {
            _tmp_1 = cursor.getInt(_cursorIndexOfIsPhishing);
          }
          _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
          final Float _tmpPhishScore;
          if (cursor.isNull(_cursorIndexOfPhishScore)) {
            _tmpPhishScore = null;
          } else {
            _tmpPhishScore = cursor.getFloat(_cursorIndexOfPhishScore);
          }
          final String _tmpReasonsJson;
          if (cursor.isNull(_cursorIndexOfReasonsJson)) {
            _tmpReasonsJson = null;
          } else {
            _tmpReasonsJson = cursor.getString(_cursorIndexOfReasonsJson);
          }
          final boolean _tmpReviewed;
          final int _tmp_2;
          _tmp_2 = cursor.getInt(_cursorIndexOfReviewed);
          _tmpReviewed = _tmp_2 != 0;
          final int _tmpVersion;
          _tmpVersion = cursor.getInt(_cursorIndexOfVersion);
          _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          _result.add(_item);
        }
        return _result;
      }
    };
  }

  @Override
  public PagingSource<Integer, MessageEntity> getNeedsReviewPaged() {
    final String _sql = "SELECT * FROM messages WHERE reviewed = 0 AND (isPhishing IS NULL OR phishScore IS NULL) ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return new LimitOffsetPagingSource<MessageEntity>(_statement, __db, "messages") {
      @Override
      @NonNull
      protected List<MessageEntity> convertRows(@NonNull final Cursor cursor) {
        final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(cursor, "id");
        final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(cursor, "sender");
        final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(cursor, "body");
        final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(cursor, "ts");
        final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(cursor, "language");
        final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(cursor, "featuresJson");
        final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(cursor, "isOtp");
        final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(cursor, "otpIntent");
        final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(cursor, "isPhishing");
        final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(cursor, "phishScore");
        final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(cursor, "reasonsJson");
        final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(cursor, "reviewed");
        final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(cursor, "version");
        final List<MessageEntity> _result = new ArrayList<MessageEntity>(cursor.getCount());
        while (cursor.moveToNext()) {
          final MessageEntity _item;
          final long _tmpId;
          _tmpId = cursor.getLong(_cursorIndexOfId);
          final String _tmpSender;
          _tmpSender = cursor.getString(_cursorIndexOfSender);
          final String _tmpBody;
          _tmpBody = cursor.getString(_cursorIndexOfBody);
          final long _tmpTs;
          _tmpTs = cursor.getLong(_cursorIndexOfTs);
          final String _tmpLanguage;
          if (cursor.isNull(_cursorIndexOfLanguage)) {
            _tmpLanguage = null;
          } else {
            _tmpLanguage = cursor.getString(_cursorIndexOfLanguage);
          }
          final String _tmpFeaturesJson;
          if (cursor.isNull(_cursorIndexOfFeaturesJson)) {
            _tmpFeaturesJson = null;
          } else {
            _tmpFeaturesJson = cursor.getString(_cursorIndexOfFeaturesJson);
          }
          final Boolean _tmpIsOtp;
          final Integer _tmp;
          if (cursor.isNull(_cursorIndexOfIsOtp)) {
            _tmp = null;
          } else {
            _tmp = cursor.getInt(_cursorIndexOfIsOtp);
          }
          _tmpIsOtp = _tmp == null ? null : _tmp != 0;
          final String _tmpOtpIntent;
          if (cursor.isNull(_cursorIndexOfOtpIntent)) {
            _tmpOtpIntent = null;
          } else {
            _tmpOtpIntent = cursor.getString(_cursorIndexOfOtpIntent);
          }
          final Boolean _tmpIsPhishing;
          final Integer _tmp_1;
          if (cursor.isNull(_cursorIndexOfIsPhishing)) {
            _tmp_1 = null;
          } else {
            _tmp_1 = cursor.getInt(_cursorIndexOfIsPhishing);
          }
          _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
          final Float _tmpPhishScore;
          if (cursor.isNull(_cursorIndexOfPhishScore)) {
            _tmpPhishScore = null;
          } else {
            _tmpPhishScore = cursor.getFloat(_cursorIndexOfPhishScore);
          }
          final String _tmpReasonsJson;
          if (cursor.isNull(_cursorIndexOfReasonsJson)) {
            _tmpReasonsJson = null;
          } else {
            _tmpReasonsJson = cursor.getString(_cursorIndexOfReasonsJson);
          }
          final boolean _tmpReviewed;
          final int _tmp_2;
          _tmp_2 = cursor.getInt(_cursorIndexOfReviewed);
          _tmpReviewed = _tmp_2 != 0;
          final int _tmpVersion;
          _tmpVersion = cursor.getInt(_cursorIndexOfVersion);
          _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          _result.add(_item);
        }
        return _result;
      }
    };
  }

  @Override
  public PagingSource<Integer, MessageEntity> getGeneralPaged() {
    final String _sql = "SELECT * FROM messages WHERE (isOtp IS NULL OR isOtp = 0) AND (isPhishing IS NULL OR isPhishing = 0) ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return new LimitOffsetPagingSource<MessageEntity>(_statement, __db, "messages") {
      @Override
      @NonNull
      protected List<MessageEntity> convertRows(@NonNull final Cursor cursor) {
        final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(cursor, "id");
        final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(cursor, "sender");
        final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(cursor, "body");
        final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(cursor, "ts");
        final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(cursor, "language");
        final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(cursor, "featuresJson");
        final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(cursor, "isOtp");
        final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(cursor, "otpIntent");
        final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(cursor, "isPhishing");
        final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(cursor, "phishScore");
        final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(cursor, "reasonsJson");
        final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(cursor, "reviewed");
        final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(cursor, "version");
        final List<MessageEntity> _result = new ArrayList<MessageEntity>(cursor.getCount());
        while (cursor.moveToNext()) {
          final MessageEntity _item;
          final long _tmpId;
          _tmpId = cursor.getLong(_cursorIndexOfId);
          final String _tmpSender;
          _tmpSender = cursor.getString(_cursorIndexOfSender);
          final String _tmpBody;
          _tmpBody = cursor.getString(_cursorIndexOfBody);
          final long _tmpTs;
          _tmpTs = cursor.getLong(_cursorIndexOfTs);
          final String _tmpLanguage;
          if (cursor.isNull(_cursorIndexOfLanguage)) {
            _tmpLanguage = null;
          } else {
            _tmpLanguage = cursor.getString(_cursorIndexOfLanguage);
          }
          final String _tmpFeaturesJson;
          if (cursor.isNull(_cursorIndexOfFeaturesJson)) {
            _tmpFeaturesJson = null;
          } else {
            _tmpFeaturesJson = cursor.getString(_cursorIndexOfFeaturesJson);
          }
          final Boolean _tmpIsOtp;
          final Integer _tmp;
          if (cursor.isNull(_cursorIndexOfIsOtp)) {
            _tmp = null;
          } else {
            _tmp = cursor.getInt(_cursorIndexOfIsOtp);
          }
          _tmpIsOtp = _tmp == null ? null : _tmp != 0;
          final String _tmpOtpIntent;
          if (cursor.isNull(_cursorIndexOfOtpIntent)) {
            _tmpOtpIntent = null;
          } else {
            _tmpOtpIntent = cursor.getString(_cursorIndexOfOtpIntent);
          }
          final Boolean _tmpIsPhishing;
          final Integer _tmp_1;
          if (cursor.isNull(_cursorIndexOfIsPhishing)) {
            _tmp_1 = null;
          } else {
            _tmp_1 = cursor.getInt(_cursorIndexOfIsPhishing);
          }
          _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
          final Float _tmpPhishScore;
          if (cursor.isNull(_cursorIndexOfPhishScore)) {
            _tmpPhishScore = null;
          } else {
            _tmpPhishScore = cursor.getFloat(_cursorIndexOfPhishScore);
          }
          final String _tmpReasonsJson;
          if (cursor.isNull(_cursorIndexOfReasonsJson)) {
            _tmpReasonsJson = null;
          } else {
            _tmpReasonsJson = cursor.getString(_cursorIndexOfReasonsJson);
          }
          final boolean _tmpReviewed;
          final int _tmp_2;
          _tmp_2 = cursor.getInt(_cursorIndexOfReviewed);
          _tmpReviewed = _tmp_2 != 0;
          final int _tmpVersion;
          _tmpVersion = cursor.getInt(_cursorIndexOfVersion);
          _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          _result.add(_item);
        }
        return _result;
      }
    };
  }

  @Override
  public PagingSource<Integer, MessageEntity> searchPaged(final String query) {
    final String _sql = "SELECT * FROM messages WHERE body LIKE ? OR sender LIKE ? ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 2);
    int _argIndex = 1;
    _statement.bindString(_argIndex, query);
    _argIndex = 2;
    _statement.bindString(_argIndex, query);
    return new LimitOffsetPagingSource<MessageEntity>(_statement, __db, "messages") {
      @Override
      @NonNull
      protected List<MessageEntity> convertRows(@NonNull final Cursor cursor) {
        final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(cursor, "id");
        final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(cursor, "sender");
        final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(cursor, "body");
        final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(cursor, "ts");
        final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(cursor, "language");
        final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(cursor, "featuresJson");
        final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(cursor, "isOtp");
        final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(cursor, "otpIntent");
        final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(cursor, "isPhishing");
        final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(cursor, "phishScore");
        final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(cursor, "reasonsJson");
        final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(cursor, "reviewed");
        final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(cursor, "version");
        final List<MessageEntity> _result = new ArrayList<MessageEntity>(cursor.getCount());
        while (cursor.moveToNext()) {
          final MessageEntity _item;
          final long _tmpId;
          _tmpId = cursor.getLong(_cursorIndexOfId);
          final String _tmpSender;
          _tmpSender = cursor.getString(_cursorIndexOfSender);
          final String _tmpBody;
          _tmpBody = cursor.getString(_cursorIndexOfBody);
          final long _tmpTs;
          _tmpTs = cursor.getLong(_cursorIndexOfTs);
          final String _tmpLanguage;
          if (cursor.isNull(_cursorIndexOfLanguage)) {
            _tmpLanguage = null;
          } else {
            _tmpLanguage = cursor.getString(_cursorIndexOfLanguage);
          }
          final String _tmpFeaturesJson;
          if (cursor.isNull(_cursorIndexOfFeaturesJson)) {
            _tmpFeaturesJson = null;
          } else {
            _tmpFeaturesJson = cursor.getString(_cursorIndexOfFeaturesJson);
          }
          final Boolean _tmpIsOtp;
          final Integer _tmp;
          if (cursor.isNull(_cursorIndexOfIsOtp)) {
            _tmp = null;
          } else {
            _tmp = cursor.getInt(_cursorIndexOfIsOtp);
          }
          _tmpIsOtp = _tmp == null ? null : _tmp != 0;
          final String _tmpOtpIntent;
          if (cursor.isNull(_cursorIndexOfOtpIntent)) {
            _tmpOtpIntent = null;
          } else {
            _tmpOtpIntent = cursor.getString(_cursorIndexOfOtpIntent);
          }
          final Boolean _tmpIsPhishing;
          final Integer _tmp_1;
          if (cursor.isNull(_cursorIndexOfIsPhishing)) {
            _tmp_1 = null;
          } else {
            _tmp_1 = cursor.getInt(_cursorIndexOfIsPhishing);
          }
          _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
          final Float _tmpPhishScore;
          if (cursor.isNull(_cursorIndexOfPhishScore)) {
            _tmpPhishScore = null;
          } else {
            _tmpPhishScore = cursor.getFloat(_cursorIndexOfPhishScore);
          }
          final String _tmpReasonsJson;
          if (cursor.isNull(_cursorIndexOfReasonsJson)) {
            _tmpReasonsJson = null;
          } else {
            _tmpReasonsJson = cursor.getString(_cursorIndexOfReasonsJson);
          }
          final boolean _tmpReviewed;
          final int _tmp_2;
          _tmp_2 = cursor.getInt(_cursorIndexOfReviewed);
          _tmpReviewed = _tmp_2 != 0;
          final int _tmpVersion;
          _tmpVersion = cursor.getInt(_cursorIndexOfVersion);
          _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          _result.add(_item);
        }
        return _result;
      }
    };
  }

  @Override
  public Flow<MessageEntity> getLatestMessage() {
    final String _sql = "SELECT * FROM messages ORDER BY ts DESC LIMIT 1";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"messages"}, new Callable<MessageEntity>() {
      @Override
      @Nullable
      public MessageEntity call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(_cursor, "sender");
          final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(_cursor, "body");
          final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(_cursor, "ts");
          final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(_cursor, "language");
          final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(_cursor, "featuresJson");
          final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(_cursor, "isOtp");
          final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(_cursor, "otpIntent");
          final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(_cursor, "isPhishing");
          final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(_cursor, "phishScore");
          final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(_cursor, "reasonsJson");
          final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(_cursor, "reviewed");
          final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(_cursor, "version");
          final MessageEntity _result;
          if (_cursor.moveToFirst()) {
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpSender;
            _tmpSender = _cursor.getString(_cursorIndexOfSender);
            final String _tmpBody;
            _tmpBody = _cursor.getString(_cursorIndexOfBody);
            final long _tmpTs;
            _tmpTs = _cursor.getLong(_cursorIndexOfTs);
            final String _tmpLanguage;
            if (_cursor.isNull(_cursorIndexOfLanguage)) {
              _tmpLanguage = null;
            } else {
              _tmpLanguage = _cursor.getString(_cursorIndexOfLanguage);
            }
            final String _tmpFeaturesJson;
            if (_cursor.isNull(_cursorIndexOfFeaturesJson)) {
              _tmpFeaturesJson = null;
            } else {
              _tmpFeaturesJson = _cursor.getString(_cursorIndexOfFeaturesJson);
            }
            final Boolean _tmpIsOtp;
            final Integer _tmp;
            if (_cursor.isNull(_cursorIndexOfIsOtp)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(_cursorIndexOfIsOtp);
            }
            _tmpIsOtp = _tmp == null ? null : _tmp != 0;
            final String _tmpOtpIntent;
            if (_cursor.isNull(_cursorIndexOfOtpIntent)) {
              _tmpOtpIntent = null;
            } else {
              _tmpOtpIntent = _cursor.getString(_cursorIndexOfOtpIntent);
            }
            final Boolean _tmpIsPhishing;
            final Integer _tmp_1;
            if (_cursor.isNull(_cursorIndexOfIsPhishing)) {
              _tmp_1 = null;
            } else {
              _tmp_1 = _cursor.getInt(_cursorIndexOfIsPhishing);
            }
            _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
            final Float _tmpPhishScore;
            if (_cursor.isNull(_cursorIndexOfPhishScore)) {
              _tmpPhishScore = null;
            } else {
              _tmpPhishScore = _cursor.getFloat(_cursorIndexOfPhishScore);
            }
            final String _tmpReasonsJson;
            if (_cursor.isNull(_cursorIndexOfReasonsJson)) {
              _tmpReasonsJson = null;
            } else {
              _tmpReasonsJson = _cursor.getString(_cursorIndexOfReasonsJson);
            }
            final boolean _tmpReviewed;
            final int _tmp_2;
            _tmp_2 = _cursor.getInt(_cursorIndexOfReviewed);
            _tmpReviewed = _tmp_2 != 0;
            final int _tmpVersion;
            _tmpVersion = _cursor.getInt(_cursorIndexOfVersion);
            _result = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          } else {
            _result = null;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Object getById(final long id, final Continuation<? super MessageEntity> $completion) {
    final String _sql = "SELECT * FROM messages WHERE id = ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    _statement.bindLong(_argIndex, id);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<MessageEntity>() {
      @Override
      @Nullable
      public MessageEntity call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(_cursor, "sender");
          final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(_cursor, "body");
          final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(_cursor, "ts");
          final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(_cursor, "language");
          final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(_cursor, "featuresJson");
          final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(_cursor, "isOtp");
          final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(_cursor, "otpIntent");
          final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(_cursor, "isPhishing");
          final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(_cursor, "phishScore");
          final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(_cursor, "reasonsJson");
          final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(_cursor, "reviewed");
          final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(_cursor, "version");
          final MessageEntity _result;
          if (_cursor.moveToFirst()) {
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpSender;
            _tmpSender = _cursor.getString(_cursorIndexOfSender);
            final String _tmpBody;
            _tmpBody = _cursor.getString(_cursorIndexOfBody);
            final long _tmpTs;
            _tmpTs = _cursor.getLong(_cursorIndexOfTs);
            final String _tmpLanguage;
            if (_cursor.isNull(_cursorIndexOfLanguage)) {
              _tmpLanguage = null;
            } else {
              _tmpLanguage = _cursor.getString(_cursorIndexOfLanguage);
            }
            final String _tmpFeaturesJson;
            if (_cursor.isNull(_cursorIndexOfFeaturesJson)) {
              _tmpFeaturesJson = null;
            } else {
              _tmpFeaturesJson = _cursor.getString(_cursorIndexOfFeaturesJson);
            }
            final Boolean _tmpIsOtp;
            final Integer _tmp;
            if (_cursor.isNull(_cursorIndexOfIsOtp)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(_cursorIndexOfIsOtp);
            }
            _tmpIsOtp = _tmp == null ? null : _tmp != 0;
            final String _tmpOtpIntent;
            if (_cursor.isNull(_cursorIndexOfOtpIntent)) {
              _tmpOtpIntent = null;
            } else {
              _tmpOtpIntent = _cursor.getString(_cursorIndexOfOtpIntent);
            }
            final Boolean _tmpIsPhishing;
            final Integer _tmp_1;
            if (_cursor.isNull(_cursorIndexOfIsPhishing)) {
              _tmp_1 = null;
            } else {
              _tmp_1 = _cursor.getInt(_cursorIndexOfIsPhishing);
            }
            _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
            final Float _tmpPhishScore;
            if (_cursor.isNull(_cursorIndexOfPhishScore)) {
              _tmpPhishScore = null;
            } else {
              _tmpPhishScore = _cursor.getFloat(_cursorIndexOfPhishScore);
            }
            final String _tmpReasonsJson;
            if (_cursor.isNull(_cursorIndexOfReasonsJson)) {
              _tmpReasonsJson = null;
            } else {
              _tmpReasonsJson = _cursor.getString(_cursorIndexOfReasonsJson);
            }
            final boolean _tmpReviewed;
            final int _tmp_2;
            _tmp_2 = _cursor.getInt(_cursorIndexOfReviewed);
            _tmpReviewed = _tmp_2 != 0;
            final int _tmpVersion;
            _tmpVersion = _cursor.getInt(_cursorIndexOfVersion);
            _result = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
          } else {
            _result = null;
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Flow<Integer> getTotalCount() {
    final String _sql = "SELECT COUNT(*) FROM messages";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"messages"}, new Callable<Integer>() {
      @Override
      @NonNull
      public Integer call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Integer _result;
          if (_cursor.moveToFirst()) {
            final int _tmp;
            _tmp = _cursor.getInt(0);
            _result = _tmp;
          } else {
            _result = 0;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Flow<Integer> getOtpCount() {
    final String _sql = "SELECT COUNT(*) FROM messages WHERE isOtp = 1";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"messages"}, new Callable<Integer>() {
      @Override
      @NonNull
      public Integer call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Integer _result;
          if (_cursor.moveToFirst()) {
            final int _tmp;
            _tmp = _cursor.getInt(0);
            _result = _tmp;
          } else {
            _result = 0;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Flow<Integer> getPhishingCount() {
    final String _sql = "SELECT COUNT(*) FROM messages WHERE isPhishing = 1";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"messages"}, new Callable<Integer>() {
      @Override
      @NonNull
      public Integer call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Integer _result;
          if (_cursor.moveToFirst()) {
            final int _tmp;
            _tmp = _cursor.getInt(0);
            _result = _tmp;
          } else {
            _result = 0;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Flow<Integer> getNeedsReviewCount() {
    final String _sql = "SELECT COUNT(*) FROM messages WHERE reviewed = 0 AND (isPhishing IS NULL OR phishScore IS NULL)";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"messages"}, new Callable<Integer>() {
      @Override
      @NonNull
      public Integer call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Integer _result;
          if (_cursor.moveToFirst()) {
            final int _tmp;
            _tmp = _cursor.getInt(0);
            _result = _tmp;
          } else {
            _result = 0;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Flow<Integer> getGeneralCount() {
    final String _sql = "SELECT COUNT(*) FROM messages WHERE (isOtp IS NULL OR isOtp = 0) AND (isPhishing IS NULL OR isPhishing = 0)";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    return CoroutinesRoom.createFlow(__db, false, new String[] {"messages"}, new Callable<Integer>() {
      @Override
      @NonNull
      public Integer call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final Integer _result;
          if (_cursor.moveToFirst()) {
            final int _tmp;
            _tmp = _cursor.getInt(0);
            _result = _tmp;
          } else {
            _result = 0;
          }
          return _result;
        } finally {
          _cursor.close();
        }
      }

      @Override
      protected void finalize() {
        _statement.release();
      }
    });
  }

  @Override
  public Object getUnclassified(final int limit,
      final Continuation<? super List<MessageEntity>> $completion) {
    final String _sql = "SELECT * FROM messages WHERE isOtp IS NULL OR isPhishing IS NULL ORDER BY ts DESC LIMIT ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    _statement.bindLong(_argIndex, limit);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<MessageEntity>>() {
      @Override
      @NonNull
      public List<MessageEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(_cursor, "sender");
          final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(_cursor, "body");
          final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(_cursor, "ts");
          final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(_cursor, "language");
          final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(_cursor, "featuresJson");
          final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(_cursor, "isOtp");
          final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(_cursor, "otpIntent");
          final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(_cursor, "isPhishing");
          final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(_cursor, "phishScore");
          final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(_cursor, "reasonsJson");
          final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(_cursor, "reviewed");
          final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(_cursor, "version");
          final List<MessageEntity> _result = new ArrayList<MessageEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final MessageEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpSender;
            _tmpSender = _cursor.getString(_cursorIndexOfSender);
            final String _tmpBody;
            _tmpBody = _cursor.getString(_cursorIndexOfBody);
            final long _tmpTs;
            _tmpTs = _cursor.getLong(_cursorIndexOfTs);
            final String _tmpLanguage;
            if (_cursor.isNull(_cursorIndexOfLanguage)) {
              _tmpLanguage = null;
            } else {
              _tmpLanguage = _cursor.getString(_cursorIndexOfLanguage);
            }
            final String _tmpFeaturesJson;
            if (_cursor.isNull(_cursorIndexOfFeaturesJson)) {
              _tmpFeaturesJson = null;
            } else {
              _tmpFeaturesJson = _cursor.getString(_cursorIndexOfFeaturesJson);
            }
            final Boolean _tmpIsOtp;
            final Integer _tmp;
            if (_cursor.isNull(_cursorIndexOfIsOtp)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(_cursorIndexOfIsOtp);
            }
            _tmpIsOtp = _tmp == null ? null : _tmp != 0;
            final String _tmpOtpIntent;
            if (_cursor.isNull(_cursorIndexOfOtpIntent)) {
              _tmpOtpIntent = null;
            } else {
              _tmpOtpIntent = _cursor.getString(_cursorIndexOfOtpIntent);
            }
            final Boolean _tmpIsPhishing;
            final Integer _tmp_1;
            if (_cursor.isNull(_cursorIndexOfIsPhishing)) {
              _tmp_1 = null;
            } else {
              _tmp_1 = _cursor.getInt(_cursorIndexOfIsPhishing);
            }
            _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
            final Float _tmpPhishScore;
            if (_cursor.isNull(_cursorIndexOfPhishScore)) {
              _tmpPhishScore = null;
            } else {
              _tmpPhishScore = _cursor.getFloat(_cursorIndexOfPhishScore);
            }
            final String _tmpReasonsJson;
            if (_cursor.isNull(_cursorIndexOfReasonsJson)) {
              _tmpReasonsJson = null;
            } else {
              _tmpReasonsJson = _cursor.getString(_cursorIndexOfReasonsJson);
            }
            final boolean _tmpReviewed;
            final int _tmp_2;
            _tmp_2 = _cursor.getInt(_cursorIndexOfReviewed);
            _tmpReviewed = _tmp_2 != 0;
            final int _tmpVersion;
            _tmpVersion = _cursor.getInt(_cursorIndexOfVersion);
            _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Object getAllMessages(final Continuation<? super List<MessageEntity>> $completion) {
    final String _sql = "SELECT * FROM messages ORDER BY ts DESC";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 0);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<MessageEntity>>() {
      @Override
      @NonNull
      public List<MessageEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfSender = CursorUtil.getColumnIndexOrThrow(_cursor, "sender");
          final int _cursorIndexOfBody = CursorUtil.getColumnIndexOrThrow(_cursor, "body");
          final int _cursorIndexOfTs = CursorUtil.getColumnIndexOrThrow(_cursor, "ts");
          final int _cursorIndexOfLanguage = CursorUtil.getColumnIndexOrThrow(_cursor, "language");
          final int _cursorIndexOfFeaturesJson = CursorUtil.getColumnIndexOrThrow(_cursor, "featuresJson");
          final int _cursorIndexOfIsOtp = CursorUtil.getColumnIndexOrThrow(_cursor, "isOtp");
          final int _cursorIndexOfOtpIntent = CursorUtil.getColumnIndexOrThrow(_cursor, "otpIntent");
          final int _cursorIndexOfIsPhishing = CursorUtil.getColumnIndexOrThrow(_cursor, "isPhishing");
          final int _cursorIndexOfPhishScore = CursorUtil.getColumnIndexOrThrow(_cursor, "phishScore");
          final int _cursorIndexOfReasonsJson = CursorUtil.getColumnIndexOrThrow(_cursor, "reasonsJson");
          final int _cursorIndexOfReviewed = CursorUtil.getColumnIndexOrThrow(_cursor, "reviewed");
          final int _cursorIndexOfVersion = CursorUtil.getColumnIndexOrThrow(_cursor, "version");
          final List<MessageEntity> _result = new ArrayList<MessageEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final MessageEntity _item;
            final long _tmpId;
            _tmpId = _cursor.getLong(_cursorIndexOfId);
            final String _tmpSender;
            _tmpSender = _cursor.getString(_cursorIndexOfSender);
            final String _tmpBody;
            _tmpBody = _cursor.getString(_cursorIndexOfBody);
            final long _tmpTs;
            _tmpTs = _cursor.getLong(_cursorIndexOfTs);
            final String _tmpLanguage;
            if (_cursor.isNull(_cursorIndexOfLanguage)) {
              _tmpLanguage = null;
            } else {
              _tmpLanguage = _cursor.getString(_cursorIndexOfLanguage);
            }
            final String _tmpFeaturesJson;
            if (_cursor.isNull(_cursorIndexOfFeaturesJson)) {
              _tmpFeaturesJson = null;
            } else {
              _tmpFeaturesJson = _cursor.getString(_cursorIndexOfFeaturesJson);
            }
            final Boolean _tmpIsOtp;
            final Integer _tmp;
            if (_cursor.isNull(_cursorIndexOfIsOtp)) {
              _tmp = null;
            } else {
              _tmp = _cursor.getInt(_cursorIndexOfIsOtp);
            }
            _tmpIsOtp = _tmp == null ? null : _tmp != 0;
            final String _tmpOtpIntent;
            if (_cursor.isNull(_cursorIndexOfOtpIntent)) {
              _tmpOtpIntent = null;
            } else {
              _tmpOtpIntent = _cursor.getString(_cursorIndexOfOtpIntent);
            }
            final Boolean _tmpIsPhishing;
            final Integer _tmp_1;
            if (_cursor.isNull(_cursorIndexOfIsPhishing)) {
              _tmp_1 = null;
            } else {
              _tmp_1 = _cursor.getInt(_cursorIndexOfIsPhishing);
            }
            _tmpIsPhishing = _tmp_1 == null ? null : _tmp_1 != 0;
            final Float _tmpPhishScore;
            if (_cursor.isNull(_cursorIndexOfPhishScore)) {
              _tmpPhishScore = null;
            } else {
              _tmpPhishScore = _cursor.getFloat(_cursorIndexOfPhishScore);
            }
            final String _tmpReasonsJson;
            if (_cursor.isNull(_cursorIndexOfReasonsJson)) {
              _tmpReasonsJson = null;
            } else {
              _tmpReasonsJson = _cursor.getString(_cursorIndexOfReasonsJson);
            }
            final boolean _tmpReviewed;
            final int _tmp_2;
            _tmp_2 = _cursor.getInt(_cursorIndexOfReviewed);
            _tmpReviewed = _tmp_2 != 0;
            final int _tmpVersion;
            _tmpVersion = _cursor.getInt(_cursorIndexOfVersion);
            _item = new MessageEntity(_tmpId,_tmpSender,_tmpBody,_tmpTs,_tmpLanguage,_tmpFeaturesJson,_tmpIsOtp,_tmpOtpIntent,_tmpIsPhishing,_tmpPhishScore,_tmpReasonsJson,_tmpReviewed,_tmpVersion);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}
